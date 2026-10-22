package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"strings"
)

const (
	browser360     = "360"
	browserDefault = "default"

	uiModeApp     = "app"
	uiModeBrowser = "browser"
)

// Site 是一个常用网址。
type Site struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	URL     string `json:"url"`
	Group   string `json:"group"`
	Browser string `json:"browser"` // browser360 或 browserDefault
}

// Config 保存在 exe 同目录的 AuditBrowse.json 中。
type Config struct {
	Browser360Path  string `json:"browser360Path"`  // 360 浏览器可执行文件路径，留空则自动探测
	IsolatedProfile bool   `json:"isolatedProfile"` // 用独立的用户数据目录启动 360，不影响本机已有的 360 配置
	UIMode          string `json:"uiMode"`          // app: 用 360 的应用窗口显示本程序界面；browser: 用系统默认浏览器
	Sites           []Site `json:"sites"`
}

func defaultConfig() *Config {
	return &Config{
		Browser360Path:  firstExisting(detect360Candidates()),
		IsolatedProfile: true,
		UIMode:          uiModeApp,
		Sites:           []Site{},
	}
}

func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		cfg := defaultConfig()
		return cfg, saveConfig(path, cfg)
	}
	if err != nil {
		return nil, err
	}
	cfg := defaultConfig()
	if err := json.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("%s 格式错误: %w", path, err)
	}
	if err := cfg.normalize(); err != nil {
		return nil, err
	}
	return cfg, nil
}

// saveConfig 先写临时文件再改名，避免写到一半断电损坏配置。
func saveConfig(path string, cfg *Config) error {
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

// normalize 校验并补全配置；网址只允许 http/https，避免配置被改成可执行本地程序的协议。
func (c *Config) normalize() error {
	if c.UIMode != uiModeApp && c.UIMode != uiModeBrowser {
		c.UIMode = uiModeApp
	}
	c.Browser360Path = strings.TrimSpace(c.Browser360Path)
	if c.Sites == nil {
		c.Sites = []Site{}
	}
	seen := map[string]bool{}
	for i := range c.Sites {
		s := &c.Sites[i]
		s.Name = strings.TrimSpace(s.Name)
		s.URL = strings.TrimSpace(s.URL)
		s.Group = strings.TrimSpace(s.Group)
		if s.Name == "" {
			return fmt.Errorf("第 %d 个网址缺少名称", i+1)
		}
		u, err := url.Parse(s.URL)
		if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" {
			return fmt.Errorf("「%s」的网址无效，必须以 http:// 或 https:// 开头", s.Name)
		}
		if s.Browser != browser360 && s.Browser != browserDefault {
			s.Browser = browserDefault
		}
		if s.ID == "" || seen[s.ID] {
			s.ID = newID()
		}
		seen[s.ID] = true
	}
	return nil
}

func newID() string {
	b := make([]byte, 6)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}
