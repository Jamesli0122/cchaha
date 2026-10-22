package main

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

// detect360Candidates 列出 360 浏览器常见安装位置。
// 注意：这些路径是按常见安装方式列的，没有在实际机器上逐一验证，探测不到时请在界面里手动指定。
func detect360Candidates() []string {
	appData := os.Getenv("APPDATA")
	local := os.Getenv("LOCALAPPDATA")
	pf := os.Getenv("ProgramFiles")
	pf86 := os.Getenv("ProgramFiles(x86)")
	var out []string
	add := func(base string, parts ...string) {
		if base != "" {
			out = append(out, filepath.Join(append([]string{base}, parts...)...))
		}
	}
	add(appData, "360se6", "Application", "360se.exe")
	add(local, "360se6", "Application", "360se.exe")
	add(pf86, "360", "360se6", "Application", "360se.exe")
	add(pf, "360", "360se6", "Application", "360se.exe")
	add(local, "360ChromeX", "Chrome", "Application", "360ChromeX.exe")
	add(appData, "360chrome", "Chrome", "Application", "360chrome.exe")
	add(pf86, "360", "360Chrome", "Chrome", "Application", "360chrome.exe")
	return out
}

func firstExisting(paths []string) string {
	for _, p := range paths {
		if st, err := os.Stat(p); err == nil && !st.IsDir() {
			return p
		}
	}
	return ""
}

// args360 生成启动 360 的参数。独立用户数据目录让这份 360 与本机已有的 360 互不干扰。
func args360(cfg *Config, dataDir, target string, appWindow bool) []string {
	var args []string
	if cfg.IsolatedProfile {
		args = append(args, "--user-data-dir="+dataDir)
	}
	if appWindow {
		return append(args, "--app="+target)
	}
	return append(args, target)
}

func startDetached(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	if err := cmd.Start(); err != nil {
		return err
	}
	return cmd.Process.Release()
}

func openDefault(target string) error {
	switch runtime.GOOS {
	case "windows":
		return startDetached("rundll32", "url.dll,FileProtocolHandler", target)
	case "darwin":
		return startDetached("open", target)
	default:
		return startDetached("xdg-open", target)
	}
}

func open360(cfg *Config, dataDir, target string, appWindow bool) error {
	if cfg.Browser360Path == "" {
		return errors.New("未找到 360 浏览器，请在「设置」里指定 360se.exe 的路径")
	}
	if _, err := os.Stat(cfg.Browser360Path); err != nil {
		return fmt.Errorf("360 浏览器路径不可用: %w", err)
	}
	if cfg.IsolatedProfile {
		if err := os.MkdirAll(dataDir, 0o755); err != nil {
			return err
		}
	}
	return startDetached(cfg.Browser360Path, args360(cfg, dataDir, target, appWindow)...)
}

func openSite(cfg *Config, dataDir string, s Site) error {
	if s.Browser == browser360 {
		return open360(cfg, dataDir, s.URL, false)
	}
	return openDefault(s.URL)
}

// openUI 显示本程序自己的界面：优先用 360 的应用窗口，失败则退回系统默认浏览器。
func openUI(cfg *Config, dataDir, target string) error {
	if cfg.UIMode == uiModeApp && cfg.Browser360Path != "" {
		if err := open360(cfg, dataDir, target, true); err == nil {
			return nil
		}
	}
	return openDefault(target)
}
