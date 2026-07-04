/**
 * PythonService.java - Python后台服务
 * 在Android后台运行Python Flask服务
 */

package com.stocktool;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

public class PythonService extends Service {

    private static final String TAG = "PythonService";
    private static final String CHANNEL_ID = "stock_channel";
    private static final int NOTIFICATION_ID = 1001;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "PythonService onCreate");
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "PythonService onStartCommand");

        // 前台服务通知
        Notification notification = new Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("A股短线决策工具")
            .setContentText("后台数据服务运行中...")
            .setSmallIcon(android.R.drawable.ic_menu_graphic)
            .setOngoing(true)
            .build();

        startForeground(NOTIFICATION_ID, notification);

        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "PythonService onDestroy");
        stopForeground(true);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "股票数据服务",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("后台行情数据刷新服务");
            channel.setShowBadge(false);

            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }
}
