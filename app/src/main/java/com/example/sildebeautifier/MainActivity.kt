package com.example.sildebeautifier

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import com.example.sildebeautifier.ui.HomeScreen
import com.example.sildebeautifier.ui.UploadScreen
import com.example.sildebeautifier.ui.theme.SildeBeautifierTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            SlideBeautifierTheme {
                SlideBeautifierApp()
            }
        }
    }
}

@Composable
fun SlideBeautifierApp() {
    var currentScreen by remember { mutableStateOf("home") }

    when (currentScreen) {
        "home" -> HomeScreen(
            onStartClick = {
                currentScreen = "upload"
            }
        )

        "upload" -> UploadScreen()
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    SildeBeautifierTheme {
        Greeting("Android")
    }
}