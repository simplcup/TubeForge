package com.tubeforge.mobile

import android.app.Activity
import android.content.res.Resources
import android.graphics.drawable.GradientDrawable
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView

object ThemeUi {
    fun dp(value: Float): Float = value * Resources.getSystem().displayMetrics.density

    fun round(
        fill: Int,
        stroke: Int? = null,
        radiusDp: Float = 14f,
        strokeDp: Float = 1f,
    ): GradientDrawable = GradientDrawable().apply {
        shape = GradientDrawable.RECTANGLE
        cornerRadius = dp(radiusDp)
        setColor(fill)
        if (stroke != null) {
            setStroke(dp(strokeDp).toInt().coerceAtLeast(1), stroke)
        }
    }

    fun apply(activity: Activity, root: View, palette: Palette) {
        activity.window.statusBarColor = palette.bg
        activity.window.navigationBarColor = palette.bg
        style(root, palette)
    }

    fun style(view: View, palette: Palette) {
        when (val role = view.tag as? String) {
            "bg" -> view.setBackgroundColor(palette.bg)
            "card" -> view.background = round(palette.card, palette.border, 18f)
            "card2" -> view.background = round(palette.card2, palette.border, 14f)
            "input" -> view.background = round(palette.input, palette.border2, 12f)
            "chip" -> view.background = round(palette.card2, palette.border, 12f)
            "thumb" -> view.background = round(palette.card2, palette.border, 10f)
            "nav" -> view.setBackgroundColor(palette.card)
            "primaryButton" -> {
                view.background = round(palette.accent, null, 12f)
                (view as? TextView)?.setTextColor(palette.onAccent)
            }
            "ghostButton" -> {
                view.background = round(palette.card2, palette.border, 12f)
                (view as? TextView)?.setTextColor(palette.text)
            }
            "title" -> (view as? TextView)?.setTextColor(palette.text)
            "muted" -> (view as? TextView)?.setTextColor(palette.muted)
            "dim" -> (view as? TextView)?.setTextColor(palette.dim)
            "accentText" -> (view as? TextView)?.setTextColor(palette.accent)
            "danger" -> (view as? TextView)?.setTextColor(palette.danger)
            "success" -> (view as? TextView)?.setTextColor(palette.success)
            "field" -> (view as? EditText)?.apply {
                setTextColor(palette.text)
                setHintTextColor(palette.dim)
            }
            "icon" -> (view as? ImageView)?.setColorFilter(palette.muted)
            "iconAccent" -> (view as? ImageView)?.setColorFilter(palette.accent)
            "iconMuted" -> (view as? ImageView)?.setColorFilter(palette.dim)
            "progress" -> (view as? ProgressBar)?.apply {
                progressTintList = android.content.res.ColorStateList.valueOf(palette.accent)
                progressBackgroundTintList = android.content.res.ColorStateList.valueOf(palette.border)
            }
            else -> Unit
        }

        if (view is ViewGroup) {
            for (index in 0 until view.childCount) {
                style(view.getChildAt(index), palette)
            }
        }
    }
}
