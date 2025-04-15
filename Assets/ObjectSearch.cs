using UnityEngine;
using System.Text;
using Newtonsoft.Json;
using System.Threading;
using System.Net;
using System.IO;
using System;

public class ObjectSearch : MonoBehaviour
{
    public Camera captureCamera; // Reference to the camera to capture from
    public string unityServerUrl = "http://localhost:5000"; // URL of the agent server

    private string objectName;
    private HttpListener httpListener;
    private Thread listenerThread;

    void Start()
    {
        StartHttpListener();
    }

    void OnDestroy()
    {
        StopHttpListener();
    }

    public void OnObjectFound(string objectName, float[] boundingBox)
    {
        // Handle the object found event here
        Debug.Log($"Object '{objectName}' found with bounding box: {boundingBox[0]}, {boundingBox[1]}, {boundingBox[2]}, {boundingBox[3]}");
    }

    private void StartHttpListener()
    {
        httpListener = new HttpListener();
        httpListener.Prefixes.Add(unityServerUrl); // Change port if needed
        httpListener.Start();

        listenerThread = new Thread(() =>
        {
            while (httpListener.IsListening)
            {
                try
                {
                    var context = httpListener.GetContext();
                    HandleRequest(context);
                }
                catch (HttpListenerException) { break; } // Listener stopped
                catch (Exception ex) { Debug.LogError(ex); }
            }
        });

        listenerThread.IsBackground = true;
        listenerThread.Start();

        Debug.Log("HTTP Listener started on ");
    }

    private void StopHttpListener()
    {
        if (httpListener != null && httpListener.IsListening)
        {
            httpListener.Stop();
            httpListener.Close();
        }

        if (listenerThread != null && listenerThread.IsAlive)
        {
            listenerThread.Abort();
        }
    }

    private void HandleRequest(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        // Handle image_from_unity/object_name=XXX
        // Return raw images pixels from the current head camera
        if (request.HttpMethod == "GET" && request.Url.AbsolutePath == "/image_from_unity" && request.QueryString["object_name"] != null)
        {
            string objectName = request.QueryString["object_name"];

            // Capture the image and return raw pixels
            byte[] rawImagePixels = CaptureImage();

            if (rawImagePixels != null)
            {
                response.ContentType = "application/octet-stream";
                response.ContentLength64 = rawImagePixels.Length;
                response.OutputStream.Write(rawImagePixels, 0, rawImagePixels.Length);
            }
            else
            {
                response.StatusCode = (int)HttpStatusCode.InternalServerError;
                byte[] buffer = Encoding.UTF8.GetBytes("Failed to capture image");
                response.ContentLength64 = buffer.Length;
                response.OutputStream.Write(buffer, 0, buffer.Length);
            }
        }
        // Handle bounds_to_unity POST request with object_name and bounding_box payload
        else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/bounds_to_unity")
        {
            using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
            {
                string payload = reader.ReadToEnd();
                var data = JsonConvert.DeserializeObject<BoundsPayload>(payload);

                if (data != null && !string.IsNullOrEmpty(data.object_name) && data.bounding_box != null)
                {
                    Debug.Log($"Received bounding box for object '{data.object_name}': [{string.Join(", ", data.bounding_box)}]");

                    response.StatusCode = (int)HttpStatusCode.OK;
                    OnObjectFound(data.object_name, data.bounding_box)
                }
                else
                {
                    response.StatusCode = (int)HttpStatusCode.BadRequest;
                    byte[] buffer = Encoding.UTF8.GetBytes("Invalid payload");
                    response.ContentLength64 = buffer.Length;
                    response.OutputStream.Write(buffer, 0, buffer.Length);
                }
            }
        }
        else
        {
            response.StatusCode = (int)HttpStatusCode.BadRequest;
            byte[] buffer = Encoding.UTF8.GetBytes("Invalid request");
            response.ContentLength64 = buffer.Length;
            response.OutputStream.Write(buffer, 0, buffer.Length);
        }

        response.OutputStream.Close();
    }

    private byte[] CaptureImage()
    {
        RenderTexture renderTexture = captureCamera.targetTexture;
        if (renderTexture == null)
        {
            renderTexture = new RenderTexture(Screen.width, Screen.height, 24);
            captureCamera.targetTexture = renderTexture;
        }

        // Capture the image
        Texture2D screenShot = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
        captureCamera.Render();

        RenderTexture.active = renderTexture;
        screenShot.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
        screenShot.Apply();

        RenderTexture.active = null;

        // Get raw pixel data
        return screenShot.GetRawTextureData();
    }

    private class BoundsPayload
    {
        public string object_name { get; set; }
        public float[] bounding_box { get; set; }
    }
}