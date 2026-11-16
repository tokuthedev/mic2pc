package com.mic2pc.app

import android.app.Activity
import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import android.widget.Toast
import androidx.core.content.FileProvider
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

data class UpdateInfo(
    val versionCode: Int,
    val versionName: String,
    val apkUrl: String,
    val changelog: String
)

object AppUpdater {

    private const val VERSION_JSON_URL =
        "https://raw.githubusercontent.com/tokuthedev/mic2pc/main/version.json"

    fun checkForUpdate(
        currentVersionCode: Int,
        onUpdateFound: (UpdateInfo) -> Unit,
        onUpToDate: () -> Unit = {},
        onError: (String) -> Unit = {}
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL(VERSION_JSON_URL)
                val conn = (url.openConnection() as HttpURLConnection).apply {
                    connectTimeout = 8000
                    readTimeout = 8000
                    requestMethod = "GET"
                    setRequestProperty("User-Agent", "mic2pc-Android-App")
                    useCaches = false
                }

                if (conn.responseCode == 200) {
                    val jsonStr = conn.inputStream.bufferedReader().use { it.readText() }
                    val json = JSONObject(jsonStr)

                    val remoteVersionCode = json.optInt("versionCode", 0)
                    val remoteVersionName = json.optString("versionName", "1.0.0")
                    val apkUrl = json.optString("apkUrl", "")
                    val changelog = json.optString("changelog", "Yeni sürüm özellikleri ve iyileştirmeler.")

                    if (remoteVersionCode > currentVersionCode && apkUrl.isNotEmpty()) {
                        val info = UpdateInfo(
                            versionCode = remoteVersionCode,
                            versionName = remoteVersionName,
                            apkUrl = apkUrl,
                            changelog = changelog
                        )
                        withContext(Dispatchers.Main) {
                            onUpdateFound(info)
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            onUpToDate()
                        }
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        onError("Sunucu yanıt kodu: ${conn.responseCode}")
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    onError(e.localizedMessage ?: "Bağlantı hatası")
                }
            }
        }
    }

    fun showUpdateDialog(activity: Activity, updateInfo: UpdateInfo) {
        val title = activity.getString(R.string.update_dialog_title, updateInfo.versionName)
        val msg = activity.getString(R.string.update_dialog_msg, updateInfo.changelog)
        val btnInstall = activity.getString(R.string.update_btn_install)
        val btnLater = activity.getString(R.string.update_btn_later)

        MaterialAlertDialogBuilder(activity)
            .setTitle(title)
            .setMessage(msg)
            .setPositiveButton(btnInstall) { _, _ ->
                startDownloadWithManager(activity, updateInfo.apkUrl, updateInfo.versionName)
            }
            .setNegativeButton(btnLater, null)
            .setCancelable(true)
            .show()
    }

    private fun startDownloadWithManager(activity: Activity, apkUrl: String, versionName: String) {
        val msg = activity.getString(R.string.toast_downloading, versionName)
        Toast.makeText(activity, msg, Toast.LENGTH_SHORT).show()

        try {
            val fileName = "mic2pc-v$versionName.apk"
            val targetDir = activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
            val oldFile = File(targetDir, fileName)
            if (oldFile.exists()) {
                oldFile.delete()
            }

            val uri = Uri.parse(apkUrl)
            val request = DownloadManager.Request(uri).apply {
                setTitle("mic2pc Güncelleniyor")
                setDescription("v$versionName APK indiriliyor...")
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalFilesDir(activity, Environment.DIRECTORY_DOWNLOADS, fileName)
                setMimeType("application/vnd.android.package-archive")
            }

            val downloadManager = activity.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            val downloadId = downloadManager.enqueue(request)

            val onCompleteReceiver = object : BroadcastReceiver() {
                override fun onReceive(context: Context?, intent: Intent?) {
                    val id = intent?.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L)
                    if (id == downloadId) {
                        try {
                            activity.unregisterReceiver(this)
                        } catch (e: Exception) {
                            // ignore
                        }

                        val query = DownloadManager.Query().setFilterById(downloadId)
                        val cursor = downloadManager.query(query)
                        if (cursor != null && cursor.moveToFirst()) {
                            val statusIndex = cursor.getColumnIndex(DownloadManager.COLUMN_STATUS)
                            val status = if (statusIndex != -1) cursor.getInt(statusIndex) else -1
                            cursor.close()

                            if (status == DownloadManager.STATUS_SUCCESSFUL) {
                                val downloadedFile = File(
                                    activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS),
                                    fileName
                                )
                                if (downloadedFile.exists()) {
                                    launchApkInstall(activity, downloadedFile)
                                }
                            } else if (status == DownloadManager.STATUS_FAILED) {
                                Toast.makeText(
                                    activity,
                                    activity.getString(R.string.toast_download_fail),
                                    Toast.LENGTH_LONG
                                ).show()
                            }
                        }
                    }
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                activity.registerReceiver(
                    onCompleteReceiver,
                    IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
                    Context.RECEIVER_EXPORTED
                )
            } else {
                activity.registerReceiver(
                    onCompleteReceiver,
                    IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
                )
            }

        } catch (e: Exception) {
            Toast.makeText(activity, "İndirme başlatılamadı: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
        }
    }

    private fun launchApkInstall(context: Context, apkFile: File) {
        try {
            // Android 8.0+ için bilinmeyen kaynaklardan yükleme izni kontrolü
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (!context.packageManager.canRequestPackageInstalls()) {
                    Toast.makeText(
                        context,
                        context.getString(R.string.toast_permission_prompt),
                        Toast.LENGTH_LONG
                    ).show()
                    val permissionIntent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                        data = Uri.parse("package:${context.packageName}")
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(permissionIntent)
                    return
                }
            }

            val apkUri: Uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                FileProvider.getUriForFile(
                    context,
                    "${context.packageName}.provider",
                    apkFile
                )
            } else {
                Uri.fromFile(apkFile)
            }

            val installIntent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(apkUri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }

            context.startActivity(installIntent)
        } catch (e: Exception) {
            val failMsg = context.getString(R.string.toast_install_fail, e.localizedMessage ?: "")
            Toast.makeText(context, failMsg, Toast.LENGTH_LONG).show()
        }
    }
}
