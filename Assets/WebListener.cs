using UnityEngine;
using System.Text;
using Newtonsoft.Json;
using System.Threading;
using System.Net;
using System.IO;
using System;
using Unity.VisualScripting.InputSystem;
using UnityEngine.LightTransport;

public class WebListener : MonoBehaviour
{
    public string unityListenerUrl = "http://localhost:5000/"; // URL of the agent server


    private string objectName;
    private HttpListener httpListener;
    private Thread listenerThread;
    private UnityMainThreadDispatcher mainThreadDispatcher;
    private string outputType = "PNG";
    private static int captureCount = 0;

    /*
     * Rotating the robot is done on the main thread, web requests are handled on a separate thread.
     * The EventWaitHandle is used to signal when the rotation is complete.
     * This allows the web request to wait for the rotation to finish before responding.
     */
    public bool asyncRotation = false; // Set to true for asynchronous rotation
    private static EventWaitHandle waitForRotation = new EventWaitHandle(false, EventResetMode.ManualReset);

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

    public void OnTurnRobot(float degrees, float speed, EventWaitHandle waitForRotation)
    {
        // Handle the turn robot event here
        Debug.Log($"Turn robot '{degrees}'");

        RobotEvents.OnTurnRobot?.Invoke(degrees, speed, waitForRotation);
    }

    public void OnSetRobotYAngle(float degrees, float speed, EventWaitHandle waitForRotation)
    {
        // Handle the turn robot event here
        RobotEvents.OnSetRobotYAngle?.Invoke(degrees, speed, waitForRotation); 
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
                catch (Exception ex)
                {
                    Debug.LogError(ex);
                }
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
        else if (request.HttpMethod == "GET" && request.Url.AbsolutePath == "/ping")
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
        string status = (code == HttpStatusCode.OK) ? "true" : "false";
        var response_data = "{ \"message\" : \"" + errmsg + "\", \"success\" : " + status + " }";
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
                if (data.angular_velocity <= 0)
                {
                    OutputMessage(response, "error: angular_velocity must be positive", HttpStatusCode.BadRequest);
                    return;
                }
                Debug.Log($"Set robot Y angle '{data.current_angle}'");
                response.StatusCode = (int) HttpStatusCode.OK;

                mainThreadDispatcher.Enqueue(() =>
                {
                    OnSetRobotYAngle(data.current_angle, data.angular_velocity, waitForRotation);
                });
                waitForRotation.WaitOne();  // Wait for the rotation to complete
                waitForRotation.Reset();    // Reset the wait handle for the next rotation
                OutputMessage(response, "robot angle successfully set", HttpStatusCode.OK);
            }
            else
            {
                OutputMessage(response, "error: aidog_rotatezaxis_absolute is missing required parameters", HttpStatusCode.BadRequest);
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
                float curangle = 0;
                bool reached_end_angle = false;
                string msg = "robot successfully turned";
                if (data.angular_velocity <= 0)
                {
                    OutputMessage(response, "error: angular_velocity must be positive", HttpStatusCode.BadRequest);
                    return;
                }
                Debug.Log($"Turn robot camera '{data.turn_angle}': [{string.Join(", ", data.direction)}]");
                response.StatusCode = (int)HttpStatusCode.OK;
                response.ContentType = "application/json";
                curangle = data.current_angle + data.turn_angle;
                // determine if end angle has been reached
                if ((data.end_angle > 0) && (curangle >= data.end_angle))
                {
                    curangle = data.end_angle;
                    reached_end_angle = true;
                    data.turn_angle = data.end_angle - data.current_angle;
                    msg = "robot at end angle";
                }
                else if ((data.end_angle <= 0) && (curangle <= data.end_angle))
                {
                    curangle = data.end_angle;
                    reached_end_angle = true;
                    data.turn_angle = data.current_angle - data.end_angle;
                    msg = "robot at end angle";
                }
                TurnResult result = new TurnResult
                {
                    last_angle = curangle,
                    at_end = reached_end_angle,
                    message = msg,
                    success = true
                };
            
                mainThreadDispatcher.Enqueue(() =>
                {
                    OnTurnRobot(data.turn_angle, data.angular_velocity, waitForRotation);
                });
                waitForRotation.WaitOne();  // Wait for the rotation to complete
                waitForRotation.Reset();    // Reset the wait handle for the next rotation
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
        byte[] imageBytes = null;
        ImageCapture capturer = null;

        // Schedule the CaptureImage call on the main thread
        mainThreadDispatcher.Enqueue(() =>
        {
            capturer = gameObject.GetComponent<ImageCapture>();
            if (capturer != null)
            {
                imageBytes = (outputType == "PNG") ? capturer.CaptureImagePNG() : capturer.CaptureImagePixels();
            }
        });

        while (imageBytes == null)
        {
            Thread.Sleep(2); // Wait for the capture to complete
        }

        var request = context.Request;
        var response = context.Response;
        if ((capturer != null) && (imageBytes != null))
        {
            //String fname = "capturedimage" + Convert.ToString(++captureCount) + ".png";
            response.ContentType = (outputType == "PNG") ? "image/png" : "application/octet-stream";
            response.ContentLength64 = imageBytes.Length;
            response.OutputStream.Write(imageBytes, 0, imageBytes.Length);
            //File.WriteAllBytes(fname, imageBytes);
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


    [System.Serializable]
    private class BoundsPayload
    {
        public string object_name;
        public float[] bounding_box;
    }


    [System.Serializable]
    public class AnglePayload
    {
        public float current_angle;
        public float angular_velocity;
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