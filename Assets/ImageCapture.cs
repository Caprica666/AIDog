using UnityEngine;

public class ImageCapture : MonoBehaviour
{
    public Camera captureCamera; // Reference to the camera to capture from
    public int TextureSize;
    private Texture2D CaptureImage()
    {
        RenderTexture renderTexture = captureCamera.targetTexture;
        if (renderTexture == null)
        {
            renderTexture = new RenderTexture(TextureSize, TextureSize, 24);
            captureCamera.targetTexture = renderTexture;
        }

        // Capture the image
        Texture2D screenShot = new Texture2D(TextureSize, TextureSize, TextureFormat.RGB24, false);
        captureCamera.Render();

        RenderTexture.active = renderTexture;
        screenShot.ReadPixels(new Rect(0, 0, TextureSize, TextureSize), 0, 0);
        screenShot.Apply();

        RenderTexture.active = null;
        return screenShot;
    }

    public byte[] CaptureImagePixels()
    {
        Texture2D texture = CaptureImage();
        return texture.GetRawTextureData();
    }

    public byte[] CaptureImagePNG()
    {
        Texture2D texture = CaptureImage();
        return texture.EncodeToPNG();
    }
}