"""
Star Android Gradle Project Generator
Authoritative Reference: STAR_ANDROID.md (Section 7)
"""

import os
import shutil
from typing import Dict, Any, Optional
from star_backend.mobile.packaging import MobileBundle
from star_backend.mobile.android.jni_bridge import AndroidJNIBridge
from star_backend.mobile.android.activity import StarActivity
from star_backend.mobile.android.surface_renderer import AndroidSurfaceRenderer
from star_backend.mobile.android.sdk import AndroidSDK


class AndroidProjectGenerator:
    """
    Generates standard Android Gradle project structures incorporating
    JNI native bridges, SurfaceView render pipelines, and embedded .starmobile bundles.
    """
    def __init__(self):
        self.sdk = AndroidSDK.find_sdk()

    def generate_project(
        self,
        bundle: MobileBundle,
        bundle_path: str,
        output_dir: str
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)
        manifest = bundle.manifest
        pkg_name = manifest.package_id
        pkg_dir = os.path.join(output_dir, "app", "src", "main", "java", *pkg_name.split("."))
        runtime_pkg_dir = os.path.join(output_dir, "app", "src", "main", "java", "org", "starlang", "runtime")
        cpp_dir = os.path.join(output_dir, "app", "src", "main", "cpp")
        assets_dir = os.path.join(output_dir, "app", "src", "main", "assets")

        os.makedirs(pkg_dir, exist_ok=True)
        os.makedirs(runtime_pkg_dir, exist_ok=True)
        os.makedirs(cpp_dir, exist_ok=True)
        os.makedirs(assets_dir, exist_ok=True)

        # 0. Android SDK Configuration (local.properties & gradle.properties)
        if self.sdk and self.sdk.is_valid:
            self.sdk.generate_local_properties(output_dir)
        else:
            with open(os.path.join(output_dir, "local.properties"), "w", encoding="utf-8") as f:
                f.write("## Android SDK local.properties\n")

        with open(os.path.join(output_dir, "gradle.properties"), "w", encoding="utf-8") as f:
            f.write("org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\nandroid.nonTransitiveRClass=true\n")

        # 1. Root settings.gradle
        with open(os.path.join(output_dir, "settings.gradle"), "w", encoding="utf-8") as f:
            f.write(f'rootProject.name = "{manifest.name}"\ninclude(":app")\n')

        # 2. Root build.gradle
        with open(os.path.join(output_dir, "build.gradle"), "w", encoding="utf-8") as f:
            f.write("""buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath "com.android.tools.build:gradle:8.2.0"
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}
""")

        # 3. app/build.gradle
        with open(os.path.join(output_dir, "app", "build.gradle"), "w", encoding="utf-8") as f:
            f.write(f"""plugins {{
    id "com.android.application"
}}

android {{
    namespace "{pkg_name}"
    compileSdk 34

    defaultConfig {{
        applicationId "{pkg_name}"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "{manifest.version}"

        ndk {{
            abiFilters "arm64-v8a", "armeabi-v7a", "x86_64"
        }}
        externalNativeBuild {{
            cmake {{
                cppFlags "-std=c++20"
            }}
        }}
    }}

    externalNativeBuild {{
        cmake {{
            path "src/main/cpp/CMakeLists.txt"
        }}
    }}

    buildTypes {{
        release {{
            minifyEnabled false
            proguardFiles getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro"
        }}
    }}
}}

dependencies {{
    implementation "androidx.appcompat:appcompat:1.6.1"
}}
""")

        # 4. AndroidManifest.xml
        perm_tags = ""
        for p in manifest.permissions:
            if p == "vibrate":
                perm_tags += '    <uses-permission android:name="android.permission.VIBRATE" />\n'
            elif p == "network":
                perm_tags += '    <uses-permission android:name="android.permission.INTERNET" />\n'

        with open(os.path.join(output_dir, "app", "src", "main", "AndroidManifest.xml"), "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

{perm_tags}
    <application
        android:allowBackup="true"
        android:label="{manifest.name}"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="{manifest.orientation}"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
""")

        # 5. Java Sources
        with open(os.path.join(pkg_dir, "MainActivity.java"), "w", encoding="utf-8") as f:
            f.write(StarActivity.generate_main_activity_java(pkg_name, manifest.name))

        with open(os.path.join(runtime_pkg_dir, "StarNativeBridge.java"), "w", encoding="utf-8") as f:
            f.write(AndroidJNIBridge.generate_java_bridge_source())

        with open(os.path.join(runtime_pkg_dir, "StarSurfaceView.java"), "w", encoding="utf-8") as f:
            f.write(AndroidSurfaceRenderer.generate_surface_view_java())

        # 6. C++ NDK Bridge & CMakeLists.txt
        with open(os.path.join(cpp_dir, "star_jni_bridge.cpp"), "w", encoding="utf-8") as f:
            f.write(AndroidJNIBridge.generate_cpp_jni_source())

        with open(os.path.join(cpp_dir, "CMakeLists.txt"), "w", encoding="utf-8") as f:
            f.write("""cmake_minimum_required(VERSION 3.22.1)
project("starnative")

add_library(starnative SHARED star_jni_bridge.cpp)

find_library(log-lib log)
find_library(android-lib android)

target_link_libraries(starnative ${log-lib} ${android-lib})
""")

        # 7. Embed .starmobile bundle into assets
        shutil.copyfile(bundle_path, os.path.join(assets_dir, "app.starmobile"))

        return output_dir
