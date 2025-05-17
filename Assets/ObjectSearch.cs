using UnityEngine;
using System.Text;
using Newtonsoft.Json;
using System.Threading;
using System.Net;
using System.IO;
using System;
using Unity.VisualScripting.InputSystem;
using UnityEngine.LightTransport;

public class ObjectSearch : MonoBehaviour
{
    public Camera captureCamera; // Reference to the camera to capture from
    public string unityListenerUrl = "http://localhost:5000/"; // URL of the agent server
    public int TextureSize;


    private string objectName;
    private HttpListener httpListener;
    private Thread listenerThread;
    private UnityMainThreadDispatcher mainThreadDispatcher;
    private string outputType = "PNG";

    void Start()
    {
        mainThreadDispatcher = UnityMainThreadDispatcher.Instance();
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

    public void OnTurnRobot(int degrees, string direction)
    {
        // Handle the turn robot event here
        Debug.Log($"Turn robot '{degrees}' degrees {direction}");
        if (direction != "clockwise")
        {
            degrees = -degrees; // Invert the angle for counter-clockwise
        }
        RobotEvents.OnTurnRobot?.Invoke(degrees); // Turn 90 degre
    }


    private void StartHttpListener()
    {
        httpListener = new HttpListener();
        httpListener.Prefixes.Add(unityListenerUrl); // Change port if needed
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
        Debug.Log("HTTP Listener started on " + unityListenerUrl);
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
        Debug.Log("HTTP Listener stopped ");
    }

    private void HandleRequest(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        if (request.HttpMethod == "GET" && request.Url.AbsolutePath == "/image_from_unity")
        {
            ImageFromUnity(context);
        }
        else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/bounds_to_unity")
        {
            BoundsToUnity(context);
        }
        else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/turn_robot_camera")
        {
            TurnRobotCamera(context);
        }
        if (request.HttpMethod == "GET" && request.Url.AbsolutePath == "/ping")
        {
            Ping(context);
        }
        else
        {
            response.StatusCode = (int) HttpStatusCode.BadRequest;
            byte[] buffer = Encoding.UTF8.GetBytes("Invalid request");
            response.ContentLength64 = buffer.Length;
            response.OutputStream.Write(buffer, 0, buffer.Length);
        }
        response.OutputStream.Close();
    }

    private void TurnRobotCamera(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
        {
            string payload = reader.ReadToEnd();
            TurnPayload data = JsonConvert.DeserializeObject<TurnPayload>(payload);
            byte[] buffer;


            if (data != null)
            {
                int curangle = data.current_angle + data.amount_to_turn;
                Debug.Log($"Turn robot camera '{data.amount_to_turn}': [{string.Join(", ", data.direction)}]");
                TurnResult result = new TurnResult
                {
                    current_angle = curangle,
                    at_start_angle = (curangle == data.start_angle)
                };
                response.StatusCode = (int) HttpStatusCode.OK;
                response.ContentType = "application/json";
                mainThreadDispatcher.Enqueue(() =>
                {
                    OnTurnRobot(data.amount_to_turn, data.direction);
                });
                
                var response_data = JsonConvert.SerializeObject(result);
                buffer = Encoding.UTF8.GetBytes(response_data);
            }
            else
            {
                response.StatusCode = (int) HttpStatusCode.BadRequest;
                buffer = Encoding.UTF8.GetBytes("Invalid payload");
            }
            response.ContentLength64 = buffer.Length;
            response.OutputStream.Write(buffer, 0, buffer.Length);
        }
    }

    private void Ping(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        response.StatusCode = (int) HttpStatusCode.OK;
        byte[] buffer = Encoding.UTF8.GetBytes("{ \"message\": \"pong\" }");
        response.ContentLength64 = buffer.Length;
        response.OutputStream.Write(buffer, 0, buffer.Length);
    }

    private void ImageFromUnity(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;
        byte[] imageBytes = null;

        // Schedule the CaptureImage call on the main thread
        mainThreadDispatcher.Enqueue(() =>
        {
            imageBytes = (outputType == "PNG") ? CaptureImagePNG() : CaptureImagePixels();
        });

        while (imageBytes == null)
        {
            Thread.Sleep(2); // Wait for the capture to complete
        }

        if (imageBytes != null)
        {
            response.ContentType = (outputType == "PNG") ? "image/png" : "application/octet-stream";
            response.ContentLength64 = imageBytes.Length;
            response.OutputStream.Write(imageBytes, 0, imageBytes.Length);
            response.OutputStream.Write(imageBytes, 0, imageBytes.Length);
//           File.WriteAllBytes("capturedimage.png", imageBytes);
            imageBytes = null;
        }
        else
        {
            response.StatusCode = (int) HttpStatusCode.InternalServerError;
            byte[] buffer = Encoding.UTF8.GetBytes("Failed to capture image");
            response.ContentLength64 = buffer.Length;
            response.OutputStream.Write(buffer, 0, buffer.Length);
        }
    }

    private void BoundsToUnity(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
        {
            string payload = reader.ReadToEnd();
            var data = JsonConvert.DeserializeObject<BoundsPayload>(payload);

            if (data != null && !string.IsNullOrEmpty(data.object_name) && data.bounding_box != null)
            {
                Debug.Log($"Received bounding box for object '{data.object_name}': [{string.Join(", ", data.bounding_box)}]");

                response.StatusCode = (int) HttpStatusCode.OK;
                OnObjectFound(data.object_name, data.bounding_box);
            }
            else
            {
                response.StatusCode = (int) HttpStatusCode.BadRequest;
                byte[] buffer = Encoding.UTF8.GetBytes("Invalid payload");
                response.ContentLength64 = buffer.Length;
                response.OutputStream.Write(buffer, 0, buffer.Length);
            }
        }
    }

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

    private byte[] CaptureImagePixels()
    {
        Texture2D texture = CaptureImage();
        return texture.GetRawTextureData();
    }

    private byte[] CaptureImagePNG()
    {
        Texture2D texture = CaptureImage();
        return texture.EncodeToPNG();
    }

    [System.Serializable]
    private class BoundsPayload
    {
        public string object_name;
        public float[] bounding_box;
    }

    [System.Serializable]
    public class TurnPayload
    {
        public int start_angle;
        public int current_angle;
        public int amount_to_turn;
        public string direction;
    }

    [System.Serializable]
    public class TurnResult
    {
        public bool at_start_angle;
        public int current_angle;
    }

}