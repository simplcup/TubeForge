package com.tubeforge.mobile

import android.app.Application

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        Notify.ensureChannel(this)
        QueueManager.init(this)
    }
}
