using UnityEngine;
using System.Collections;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class ObjectSearch : MonoBehaviour
{
    public Camera captureCamera; // Reference to the camera to capture from
    public string agentServerUrl = "http://localhost:8000"; // URL of the agent server

    private string objectName;
    private bool isSearching = false;

    public async void StartObjectSearch(string objectName)
    {
        this.objectName = objectName;
        isSearching = true;

        // Notify the agent server to start the object request
        using (HttpClient client = new HttpClient())
        {
            var content = new StringContent(JsonConvert.SerializeObject(new { object_name = objectName }), Encoding.UTF8, "application/json");
            var response = await client.PostAsync(agentServerUrl + "/start_object_request", content);

            if (response.IsSuccessStatusCode)
            {
                Debug.Log("Object search started for: " + objectName);
                StartCoroutine(SendImagesToAgent());
            }
            else
            {
                Debug.LogError("Failed to start object search: " + response.ReasonPhrase);
            }
        }
    }

    private IEnumerator SendImagesToAgent()
    {
        RenderTexture renderTexture = captureCamera.targetTexture;
        if (renderTexture == null)
        {
            renderTexture = new RenderTexture(Screen.width, Screen.height, 24);
            captureCamera.targetTexture = renderTexture;
        }

        while (isSearching)
        {
            // Capture the image
            Texture2D screenShot = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
            captureCamera.Render();

            RenderTexture.active = renderTexture;
            screenShot.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
            screenShot.Apply();

            RenderTexture.active = null;

            // Get raw pixel data
            byte[] rawImageData = screenShot.GetRawTextureData();

            // Send the image to the agent server
            using (HttpClient client = new HttpClient())
            {
                var content = new StringContent(JsonConvert.SerializeObject(new { object_name = objectName, raw_image = rawImageData }), Encoding.UTF8, "application/json");
                var task = client.PostAsync(agentServerUrl + "/send_image", content);

                yield return new WaitUntil(() => task.IsCompleted);

                if (task.Result.IsSuccessStatusCode)
                {
                    Debug.Log("Image sent successfully.");

                    // Process the response
                    var responseContent = task.Result.Content.ReadAsStringAsync().Result;
                    var boundingBox = JsonConvert.DeserializeObject<BoundingBoxResponse>(responseContent);

                    if (boundingBox != null && boundingBox.success)
                    {
                        Debug.Log($"Bounding Box: X={boundingBox.bounding_box[0]}, Y={boundingBox.bounding_box[1]}, Width={boundingBox.bounding_box[2] - boundingBox.bounding_box[0]}, Height={boundingBox.bounding_box[3] - boundingBox.bounding_box[1]}");
                    }
                    else
                    {
                        Debug.LogError("Object not found in the image.");
                    }
                }
                else
                {
                    Debug.LogError("Failed to send image: " + task.Result.ReasonPhrase);
                }
            }

            // Wait for a short interval before sending the next image
            yield return new WaitForSeconds(0.5f);
        }

        // Cleanup if a new RenderTexture was created
        if (captureCamera.targetTexture != renderTexture)
        {
            Destroy(renderTexture);
        }
    }

    public void StopObjectSearch()
    {
        isSearching = false;
        Debug.Log("Object search stopped.");
    }

    private class BoundingBoxResponse
    {
        public bool success { get; set; }
        public string object_name { get; set; } // Name of the object
        public float[] bounding_box { get; set; } // [x_min, y_min, x_max, y_max]
    }
}