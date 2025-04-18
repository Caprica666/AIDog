using UnityEngine;
using UnityEngine.UI;
using System.Net.Http;
using TMPro;
using System.Threading.Tasks;


public class MCPAgentUI : MonoBehaviour
{
    public Button startButton;
    public Button stopButton;

    public TMP_Text statusText;

    private HttpClient httpClient;


    void Start()
    {
        httpClient = new HttpClient();

        // Assign button click handlers
        startButton.onClick.AddListener(OnStartButtonClick);
        stopButton.onClick.AddListener(OnStopButtonClick);
    }
    

    private async Task<bool> IsServerRunning()
    {
        string agentServerUrl = "http://localhost:5001";

        try
        {
            HttpResponseMessage response = await httpClient.GetAsync(agentServerUrl + "/ping");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private async void OnStartButtonClick()
    {
        statusText.text = "Starting server...";
        bool isRunning = await IsServerRunning();
        statusText.text = isRunning ? "Server is running." : "Failed to start server.";
    }

    private void OnStopButtonClick()
    {
        statusText.text = "Stopping server...";
        // Add logic to stop the server if needed
        statusText.text = "Server stopped.";
    }

    private void OnApplicationQuit()
    {
    }


    void OnDestroy()
    {
        httpClient.Dispose();
    }
}