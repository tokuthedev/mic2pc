package com.mic2pc.app

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

data class UpdateInfo(
    val versionCode: Int,
    val versionName: String,
    val apkUrl: String,
    val changelog: String
)

object AppUpdater {

    // GitHub üzerinden en son sürüm bilgilerini çeken adres
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
                    useCaches = false
                }

                if (conn.responseCode == 200) {
                    val jsonStr = conn.inputStream.bufferedReader().use { it.readText() }
                    val json = JSONObject(jsonStr)

                    val remoteVersionCode = json.optInt("versionCode", 0)
                    val remoteVersionName = json.optString("versionName", "1.0.0")
                    val apkUrl = json.optString("apkUrl", "")
                    val changelog = json.optString("changelog", "Performans ve hata düzeltmeleri.")

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
                        onError("Sunucu yanıtı: ${conn.responseCode}")
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
        MaterialAlertDialogBuilder(activity)
            .setTitle("🚀 Yeni Güncelleme: v${updateInfo.versionName}")
            .setMessage("${updateInfo.changelog}\n\nŞimdi indirmek ve güncellemek istiyor musunuz?")
            .setPositiveButton("Hemen Güncelle") { _, _ ->
                startDownloadAndInstall(activity, updateInfo.apkUrl)
            }
            .setNegativeButton("Daha Sonra", null)
            .setCancelable(true)
            .show()
    }

    private fun startDownloadAndInstall(activity: Activity, apkUrl: String) {
        // Android 8.0+ için bilinmeyen kaynaklardan yükleme izni kontrolü
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!activity.packageManager.canRequestPackageInstalls()) {
                val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                    data = Uri.parse("package:${activity.packageName}")
                }
                activity.startActivity(intent)
            }
        }

        // İndirme göstergesi dialog'u
        val progressDialog = MaterialAlertDialogBuilder(activity)
            .setTitle("mic2pc Güncelleniyor")
            .setMessage("Yeni sürüm indiriliyor, lütfen bekleyin...")
            .setCancelable(false)
            .create()

        progressDialog.show()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL(apkUrl)
                val conn = (url.openConnection() as HttpURLConnection).apply {
                    connectTimeout = 15000
                    readTimeout = 30000
                    requestMethod = "GET"
                }

                val downloadDir = activity.getExternalFilesDir(null) ?: activity.cacheDir
                val apkFile = File(downloadDir, "mic2pc-update.apk")
                if (apkFile.exists()) apkFile.delete()

                val inputStream = conn.inputStream
                val outputStream = FileOutputStream(apkFile)

                val buffer = ByteArray(4096)
                var bytesRead: Int
                while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                    outputStream.write(buffer, 0, bytesRead)
                }

                outputStream.flush()
                outputStream.close()
                inputStream.close()

                withContext(Dispatchers.Main) {
                    progressDialog.dismiss()
                    launchApkInstall(activity, apkFile)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    progressDialog.dismiss()
                    MaterialAlertDialogBuilder(activity)
                        .setTitle("İndirme Hatası")
                        .setMessage("Güncelleme indirilemedi: ${e.localizedMessage}")
                        .setPositiveButton("Tamam", null)
                        .show()
                }
            }
        }
    }

    private fun launchApkInstall(context: Context, apkFile: File) {
        if (!apkFile.exists()) return

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
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION
        }

        context.startActivity(installIntent)
    }
}
