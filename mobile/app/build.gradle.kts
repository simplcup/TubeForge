plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.tubeforge.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.tubeforge.mobile"
        minSdk = 29
        targetSdk = 35
        versionCode = 2
        versionName = "1.0.1"
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("debug")
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = false
    }

    packaging {
        jniLibs {
            // youtubedl-android reads libpython.zip.so / libffmpeg.zip.so from
            // nativeLibraryDir, so the libs must stay extracted on disk.
            useLegacyPackaging = true
        }
        resources {
            // Keep every licence / notice file that the bundled libraries ship.
            // Apache-2.0 requires NOTICE files to travel with the binary, and the
            // GPL-3.0 engine's notices must stay readable inside the APK.
            excludes += setOf(
                "META-INF/*.kotlin_module"
            )
        }
    }

    lint {
        abortOnError = false
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("io.github.junkfood02.youtubedl-android:library:0.17.4")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:0.17.4")
}
