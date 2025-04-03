#include <windows.h>

#pragma comment(lib, "User32.lib")

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    if (CreateProcess(
            NULL,
            (LPSTR)"conda run -n wwa-cuda python main.py",
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
