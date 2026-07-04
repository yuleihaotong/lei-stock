/**
 * StockActivity.java - Android Activity入口
 * 配合Python-for-Android使用，提供WebView容器
 * 
 * 编译后放在: android/StockActivity.java
 * buildozer会自动处理Java文件
 */

package com.stocktool;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

/**
 * 主Activity - 加载WebView显示股票工具界面
 * 后台Python服务在127.0.0.1:5000提供API
 */
public class StockActivity extends Activity {

    private WebView webView;
    private Handler handler = new Handler();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 创建全屏WebView
        webView = new WebView(this);
        setContentView(webView);

        // 配置WebView
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setDefaultTextEncodingName("UTF-8");

        // 调试
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        // 客户端配置
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                // 处理外部链接
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    if (url.contains("127.0.0.1") || url.contains("localhost")) {
                        view.loadUrl(url);
                        return true;
                    }
                    // 外部链接用浏览器打开
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                }
                return false;
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, 
                                         String description, String failingUrl) {
                super.onReceivedError(view, errorCode, description, failingUrl);
                // 加载错误时显示重试页面
                String errorHtml = String.format(
                    "<html><body style='background:#0d1117;color:#e6edf3;text-align:center;padding-top:100px;'>" +
                    "<h2>⚠️ 连接失败</h2>" +
                    "<p>%s</p>" +
                    "<button onclick='location.reload()' style='padding:10px 30px;margin-top:20px;'>重试</button>" +
                    "</body></html>",
                    description
                );
                view.loadDataWithBaseURL(null, errorHtml, "text/html", "UTF-8", null);
            }
        });

        webView.setWebChromeClient(new WebChromeClient());

        // 添加JavaScript接口，供前端调用Android原生功能
        webView.addJavascriptInterface(new AndroidBridge(), "Android");

        // 加载应用（延迟等待Python服务器启动）
        handler.postDelayed(() -> {
            loadApp();
        }, 2000);
    }

    /**
     * 加载应用界面
     * 首选加载本地前端文件，失败则尝试连接API服务器
     */
    private void loadApp() {
        try {
            // 先尝试加载API服务器（由Python启动的Flask服务）
            webView.loadUrl("http://127.0.0.1:5000/");
        } catch (Exception e) {
            // 如果失败了，加载内置的静态页面
            try {
                String staticDir = getFilesDir() + "/app/frontend";
                webView.loadUrl("file://" + staticDir + "/index.html");
            } catch (Exception e2) {
                webView.loadData(
                    "<html><body style='background:#0d1117;color:#e6edf3;text-align:center;padding-top:100px;'>" +
                    "<h2>加载失败</h2><p>请重启应用</p></body></html>",
                    "text/html", "UTF-8"
                );
            }
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (webView != null) {
            webView.destroy();
        }
    }

    /**
     * Android桥接 - 供JavaScript调用
     */
    public class AndroidBridge {
        @android.webkit.JavascriptInterface
        public void showToast(String message) {
            handler.post(() -> 
                Toast.makeText(StockActivity.this, message, Toast.LENGTH_SHORT).show()
            );
        }

        @android.webkit.JavascriptInterface
        public String getAppVersion() {
            return "1.0.0";
        }
    }
}
