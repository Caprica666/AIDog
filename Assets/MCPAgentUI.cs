using UnityEngine;
using UnityEngine.UI;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;
using TMPro; // Add this at the top of the file

public class MCPAgentUI : MonoBehaviour
{
    public Button startButton;
    public Button stopButton;

    public TMP_Text responseText;

    private HttpClient httpClient;

    private Process mcpServerProcess;


    void Start()
    {
        httpClient = new HttpClient();
    }

    private async Task<bool> IsServerRunning()
    {
        string agentServerUrl = "http://localhost:8000"; // Replace with the server's health check or root endpoint

        try
        {
            HttpResponseMessage response = await httpClient.GetAsync(agentServerUrl);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private void StartMCPServer()
    {
        string pythonPath = @"C:\Users\nolad\miniconda3\python.exe"; // Path to Python executable
        string scriptPath = @"c:\projects\Unity\AIDog\UnityMCPAgent\unity_connection.py"; // Path to the MCP server script


        ProcessStartInfo startInfo = new ProcessStartInfo
        {
            FileName = pythonPath,
            Arguments = scriptPath,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        mcpServerProcess = new Process
        {
            StartInfo = startInfo
        };

        mcpServerProcess.OutputDataReceived += (sender, args) => UnityEngine.Debug.Log(args.Data);
        mcpServerProcess.ErrorDataReceived += (sender, args) => UnityEngine.Debug.LogError(args.Data);

        mcpServerProcess.Start();
        mcpServerProcess.BeginOutputReadLine();
        mcpServerProcess.BeginErrorReadLine();

        responseText.text = "MCP server started.";
    }

    private void StopMCPServer()
    {
        if (mcpServerProcess != null && !mcpServerProcess.HasExited)
        {
            mcpServerProcess.Kill();
            responseText.text = "MCP server stopped.";
        }
    }

    private void OnApplicationQuit()
    {
        StopMCPServer();
    }


    void OnDestroy()
    {
        httpClient.Dispose();
    }
}