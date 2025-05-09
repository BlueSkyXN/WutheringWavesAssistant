#include <windows.h>

#pragma comment(lib, "User32.lib")

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    // === 执行 git pull ===
    if (CreateProcess(
            NULL,
            // (LPSTR)"git pull",
            // (LPSTR)"cmd.exe /c git pull",
            (LPSTR)"powershell.exe -Command \"git pull\"",
            NULL,
            NULL,
            FALSE,
            CREATE_NO_WINDOW,
            NULL,
            NULL,
            &si,
            &pi
    )) {
        // 等待 git pull 完成
        WaitForSingleObject(pi.hProcess, INFINITE);

        DWORD exitCode = 0;
        GetExitCodeProcess(pi.hProcess, &exitCode);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);

        if (exitCode != 0) {
            MessageBox(NULL, "Git pull failed. Please resolve conflicts or check network.", "Git Error", MB_OK | MB_ICONERROR);
            return 1;  // 结束程序
        }

    } else {
        MessageBox(NULL, "Failed to execute 'git pull'.", "Git Error", MB_OK | MB_ICONERROR);
        return 1;  // 结束程序
    }

    // === 执行 conda run ===
    if (CreateProcess(
            NULL,
            // (LPSTR)"conda run -n wwa-cuda python main.py",
            // (LPSTR)"cmd.exe /c conda run -n wwa-cuda python main.py",
            (LPSTR)"powershell.exe -Command \"conda run -n wwa-cuda python main.py\"",
            NULL,
            NULL,
            FALSE,
            CREATE_NO_WINDOW,
            NULL,
            NULL,
            &si,
            &pi
    )) {
        // 立即关闭 wwa.exe，不等待 conda run 退出
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        MessageBox(NULL, "Failed to start process.", "Error", MB_OK | MB_ICONERROR);
    }

    return 0;
}