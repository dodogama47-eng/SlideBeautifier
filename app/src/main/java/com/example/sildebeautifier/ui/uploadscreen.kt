package com.example.sildebeautifier.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun UploadScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "Upload Slides")

        Button(
            onClick = { },
            modifier = Modifier.padding(top = 24.dp)
        ) {
            Text(text = "Choose Original PPTX")
        }

        Button(
            onClick = { },
            modifier = Modifier.padding(top = 16.dp)
        ) {
            Text(text = "Choose Style PPTX")
        }

        Button(
            onClick = { },
            modifier = Modifier.padding(top = 32.dp)
        ) {
            Text(text = "Beautify")
        }
    }
}