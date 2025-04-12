using UnityEngine;
using System.Collections;
using System.Net.Http;

public class CameraCapture : MonoBehaviour
{
    public Camera captureCamera; // Reference to the camera to capture from
    public string endpointUrl = "http://localhost:5000/upload"; // REST endpoint URL for UnityMCPAgent

    public void CaptureImage()
    {
        if (captureCamera == null)
        {
            Debug.LogError("Capture Camera is not assigned.");
            return;
        }

        StartCoroutine(CaptureAndSendRawImage());
    }

    private IEnumerator CaptureAndSendRawImage()
    {
        // Set up a RenderTexture
        RenderTexture renderTexture = new RenderTexture(Screen.width, Screen.height, 24);
        captureCamera.targetTexture = renderTexture;

        // Render the camera's view
        Texture2D screenShot = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
        captureCamera.Render();

        // Read pixels from the RenderTexture
        RenderTexture.active = renderTexture;
        screenShot.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
        screenShot.Apply();

        // Reset the camera's target texture and RenderTexture
        captureCamera.targetTexture = null;
        RenderTexture.active = null;
        Destroy(renderTexture);

        // Get raw pixel data
        byte[] rawImageData = screenShot.GetRawTextureData();

        // Send the raw image data to the REST endpoint
        using (HttpClient client = new HttpClient())
        {
            HttpContent content = new ByteArrayContent(rawImageData);
            content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/octet-stream");

            HttpResponseMessage response = null;
            yield return client.PostAsync(endpointUrl, content).ContinueWith(task =>
            {
                response = task.Result;
            });

            if (response != null && response.IsSuccessStatusCode)
            {
                Debug.Log("Raw image data successfully sent to the UnityMCPAgent endpoint.");
            }
            else
            {
                Debug.LogError("Failed to send raw image data to the UnityMCPAgent endpoint.");
            }
        }
    }
}