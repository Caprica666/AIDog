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
    public TMP_InputField instructionInput; // Replace InputField with TMP_InputField
    public Button askAgent;
    public TMP_Text responseText;

    private HttpClient httpClient;
    private Process mcpAgentProcess;

    private Process mcpServerProcess;


    void Start()
    {
        httpClient = new HttpClient();

        startButton.onClick.AddListener(StartAgent);
        stopButton.onClick.AddListener(StopAgent);
        askAgent.onClick.AddListener(SendInstruction);
    }

    private async Task<bool> IsServerRunning()
    {
        string url = "http://localhost:8000"; // Replace with the server's health check or root endpoint

        try
        {
            HttpResponseMessage response = await httpClient.GetAsync(url);
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
        string scriptPath = @"c:\projects\Unity\AIDog\UnityMCPAgent\agent.py"; // Path to the MCP server script


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

    private void OnApplicationQuit()
    {
        if (mcpServerProcess != null && !mcpServerProcess.HasExited)
        {
            mcpServerProcess.Kill();
            responseText.text = "MCP server stopped.";
        }
    }

    async void StartAgent()
    {
        if (!await IsServerRunning())
        {
            StartMCPServer();
        }
        if (mcpAgentProcess == null || mcpAgentProcess.HasExited)
        {
            await Task.Run(() =>
            {
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = "UnityMCPAgent/agent.py",
                    WorkingDirectory = @"c:\\projects\\Unity\\AIDog",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };

                mcpAgentProcess = Process.Start(startInfo);
            });

            responseText.text = "Agent started successfully.";
        }
        else
        {
            responseText.text = "Agent is already running.";
        }
    }

    async void StopAgent()
    {
        if (mcpAgentProcess != null && !mcpAgentProcess.HasExited)
        {
            mcpAgentProcess.Kill();
            mcpAgentProcess = null;
            responseText.text = "Agent stopped successfully.";
        }
        else
        {
            responseText.text = "Agent is not running.";
        }
        if (!await IsServerRunning())
        {
            OnApplicationQuit();
        }
    }

    async void SendInstruction()
    {
        string instruction = instructionInput.text;
        if (string.IsNullOrEmpty(instruction))
        {
            responseText.text = "Please enter an instruction.";
            return;
        }

        string url = "http://localhost:8000/process_user_instruction"; // Replace with actual instruction endpoint
        var content = new StringContent($"{{\"instruction\":\"{instruction}\"}}", Encoding.UTF8, "application/json");

        HttpResponseMessage response = await httpClient.PostAsync(url, content);
        if (response.IsSuccessStatusCode)
        {
            string result = await response.Content.ReadAsStringAsync();
            responseText.text = $"Response: {result}";
        }
        else
        {
            responseText.text = "Failed to send instruction.";
        }
    }

    void OnDestroy()
    {
        httpClient.Dispose();
    }
}