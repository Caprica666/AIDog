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
        Debug.Log($"Turn robot '{degrees}'");

        RobotEvents.OnTurnRobot?.Invoke(degrees);
    }

    public void OnSetRobotYAngle(int degrees)
    {
        // Handle the turn robot event here
        Debug.Log($"Set robot Y angle to {degrees}");
        RobotEvents.OnSetRobotYAngle?.Invoke(degrees); 
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

        if (request.HttpMethod == "GET" && request.Url.AbsolutePath == "/aidog_get_camera_image")
        {
            ImageFromUnity(context);
        }
        else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/aidog_set_bounds")
        {
            BoundsToUnity(context);
        }
        else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/aidog_rotatezaxis_relative")
        {
            TurnRobotCamera(context);
        }
        else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/aidog_rotatezaxis_absolute")
        {
            SetRobotYAngle(context);
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

    private void OutputMessage(HttpListenerResponse response, string errmsg, HttpStatusCode code)
    {
        byte[] buffer;

        response.ContentType = "application/json";
        response.StatusCode = (int) code;
        var response_data = "{ \"status\" : \"" + errmsg + "\" }";
        buffer = Encoding.UTF8.GetBytes(response_data);
        response.ContentLength64 = buffer.Length;
        response.OutputStream.Write(buffer, 0, buffer.Length);
    }

    private void SetRobotYAngle(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
        {
            string payload = reader.ReadToEnd();
            AnglePayload data;

            try
            {
                data = JsonConvert.DeserializeObject<AnglePayload>(payload);
            }
            catch (Exception ex)
            {
                OutputMessage(response, "error: " + ex.Message, HttpStatusCode.BadRequest);
                return;
            }

            if (data != null)
            {
                Debug.Log($"Set robot Y angle '{data.current_angle}'");
                response.StatusCode = (int) HttpStatusCode.OK;

                mainThreadDispatcher.Enqueue(() =>
                {
                    OnSetRobotYAngle(data.current_angle);
                });
                OutputMessage(response, "robot angle successfully set", HttpStatusCode.OK);
            }
            else
            {
                OutputMessage(response, "error: set_robot_yangle is missing required parameters", HttpStatusCode.BadRequest);
            }
        }
    }

    private void TurnRobotCamera(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
        {
            string payload = reader.ReadToEnd();
            byte[] buffer;
            TurnPayload data;

            try
            {
                data = JsonConvert.DeserializeObject<TurnPayload>(payload);
            }
            catch (Exception ex)
            {
                OutputMessage(response, "error: " + ex.Message, HttpStatusCode.BadRequest);
                return;
            }

            if (data != null)
            {
                int curangle;
                bool reached_end_angle = false;
                string msg = "robot successfully turned";
                Debug.Log($"Turn robot camera '{data.turn_angle}': [{string.Join(", ", data.direction)}]");
                response.StatusCode = (int)HttpStatusCode.OK;
                response.ContentType = "application/json";
                
                // determine if end angle has been reached
                if ((data.end_angle > 0) && (curangle >= data.end_angle))
                {
                    curangle = data.end_angle;
                    reached_end_angle = true;
                    data.amount_to_turn = data.end_angle - data.current_angle;
                    msg = "robot at end angle";
                }
                else if ((data.end_angle <= 0) && (curangle <= data.end_angle))
                {
                    curangle = data.end_angle;
                    reached_end_angle = true;
                    data.amount_to_turn = data.current_angle - data.end_angle;
                    msg = "robot at end angle";
                }
                TurnResult result = new TurnResult
                {
                    current_angle = curangle,
                    at_end = reached_end_angle,
                    message = msg
                };

                mainThreadDispatcher.Enqueue(() =>
                {
                    OnTurnRobot(data.turn_angle, data.angular_velocity);
                });

                var response_data = JsonConvert.SerializeObject(result);
                buffer = Encoding.UTF8.GetBytes(response_data);
            }
            else
            {
                OutputMessage(response, "error: turn_robot_camera is missing required parameters", HttpStatusCode.BadRequest);
                return;
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
            //File.WriteAllBytes("capturedimage.png", imageBytes);
            imageBytes = null;
        }
        else
        {
            response.StatusCode = (int) HttpStatusCode.InternalServerError;
            byte[] buffer = Encoding.UTF8.GetBytes("Failed to capture image");
            response.ContentLength64 = buffer.Length;
            response.OutputStream.Write(buffer, 0, buffer.Length);
            //File.WriteAllBytes("capturedimage.png", imageBytes);
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
    public class AnglePayload
    {
        public int current_angle;
    }

    [System.Serializable]
    public class TurnPayload
    {
        public float turn_angle;
        public float current_angle;
        public float angular_velocity;
        public float end_angle;
        public string direction;
    }

    [System.Serializable]
    public class TurnResult
    {
        public bool at_end;
        public bool success;
        public float last_angle;
        public float elapsed_time;
        public string message;
    }

}