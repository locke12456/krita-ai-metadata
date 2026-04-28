# Krita AI Metadata Export

**版本：** 0.20  
**授權：** MIT

Krita AI Metadata Export 是一個 Krita 外掛，用來將圖層或匯出群組輸出成 PNG，並同時產生 JSON sidecar 與可選的 batch manifest。

0.20 版加入 Krita 5 / Krita 6 相容流程，以及可獨立運作的手動 metadata 匯出模式。Krita AI Diffusion 仍可用於讀取 AI 生成 prompt metadata，但即使沒有安裝 Krita AI Diffusion，基本的分組、預覽、PNG 匯出、JSON sidecar 與 manifest 工作流程仍可使用。

![Krita AI Metadata Export overview](images/overview-krita-ai-export.png)

## 0.20 版重點

- 支援 Krita 5 / Krita 6 的外掛註冊與 docker 開啟流程
- 新增不依賴 Krita AI Diffusion 的手動 metadata 匯出模式
- 可從選取圖層或匯出群組輸出 PNG 與 JSON sidecar
- 使用 `0001-chibi` 這類可讀、連號的匯出 key
- 支援選取圖層的 auto map 工作流程
- Metadata mapping 會保存到 `.kra` 文件中
- Preview panel 可檢查 resolved / unresolved 匯出目標
- 支援 batch `manifest.json`
- 改善圖層移動、刪除舊群組、重新 auto map 後的穩定性
- 修正 stale group record 可能重用舊 seed 的問題
- 手動模式不再顯示不相關的 Krita AI unavailable 警告

## 這個外掛做什麼

這個外掛的目標是：當 Krita 文件中的生成圖層經過編輯、整理、分組、重新命名或準備發布後，仍能讓輸出的圖片和對應 metadata 維持正確關係。

適合用於：

- 將選取的生成圖層輸出成 PNG
- 替每張 PNG 產生對應 JSON metadata
- 用穩定檔名管理 batch 輸出
- 在 Krita AI Diffusion metadata 可用時保留生成參數
- 在 Krita AI Diffusion 不可用時仍能輸出手動整理的作品
- 寫檔前先預覽輸出狀態

## 系統需求

### 必要

- Krita，並啟用 Python plugin 支援
- 可寫入的輸出資料夾

### 可選

- Krita AI Diffusion

Krita AI Diffusion 只在需要讀取 AI prompt 與生成 metadata 時才是必要的。手動分組與基本 PNG / JSON 匯出不依賴它。

## 安裝方式

1. 下載或 clone 此 repository。
2. 將外掛資料夾複製到 Krita 的 Python plugin 目錄。
3. 重新啟動 Krita。
4. 在 Krita 的 Python Plugin Manager 啟用外掛。
5. 從 Krita 的 Docker menu 開啟 Metadata Export docker。

## 基本使用流程

![Layout](images/layout.png)

### 1. 開啟 Metadata Export docker

Docker 會提供：

- Runtime mode label
- 目前文件狀態
- 圖層選取控制
- 圖層清單與 metadata sync 狀態
- 手動 group label 輸入
- 輸出資料夾設定
- 匯出選項
- Preview log
- Export result log

### 2. 使用 AI-enabled 模式或手動模式

當 Krita AI Diffusion metadata 可用時，外掛可以從 metadata snapshot 或 job history 解析 prompt metadata。

![AI metadata overview](images/overview-krita-ai-export.png)

當 Krita AI Diffusion 不可用時，外掛會使用手動 metadata 匯出模式。

![Krita 6 manual mode export](images/overview-krita-6-manual-mode-export.png)

手動模式仍保留以下流程：

- 選取圖層或群組
- 建立匯出群組
- 預覽匯出目標
- 匯出 PNG
- 寫出 JSON sidecar
- 寫出 manifest

手動模式不會自行產生不存在的 prompt、seed、sampler 或 model 資訊。

### 3. 篩選並選取圖層

可使用圖層清單篩選器控制顯示內容：

- Synced / inherited
- Unsynced
- Visible
- Hidden
- Groups
- Layers

你可以把目前 Krita 的 selection 匯入外掛 selection，再決定要 mapping 或匯出的圖層。

### 4. 輸入 group label

在 mapping 選取圖層前，先輸入容易閱讀的 group label。

範例：

~~~text
chibi
~~~

外掛會建立適合匯出的名稱：

~~~text
[0001] - chibi
0001-chibi.png
0001-chibi.json
~~~

如果一次選取多個圖層，會建立連號 target：

~~~text
0001-chibi.png
0002-chibi.png
0003-chibi.png
0004-chibi.png
~~~

Seed 會在可用時保存於 metadata，但不會作為 group name 或 filename。

### 5. Auto map selected layers

點擊 **Auto map selected layers**。

![Auto map selected layers](images/auto-map.png)

Auto mapping 會建立 metadata export group，並將 mapping 保存到 `.kra` 文件中。

這讓之後即使圖層被重新整理，也能從文件內保存的 snapshot 解析 metadata。

0.20 版也修正了某些 stale record 狀況：例如把 layer 移出舊 group、刪除舊 group、再 auto map 時，可能沿用舊 group seed 的問題。

### 6. 選擇輸出資料夾

如果目前文件已儲存，輸出資料夾可以跟隨 `.kra` 所在位置。

如果目前文件尚未儲存，外掛可以使用 home export folder，例如：

~~~text
~/krita_ai_metadata_export
~~~

也可以點擊 **Browse** 手動選擇資料夾。

### 7. 設定匯出選項

常用選項包含：

- Export mode
- Overwrite existing files
- Allow unresolved export
- Write manifest
- Include invisible selected targets

本版本主要輸出格式為 PNG。

### 8. Preview export

寫出檔案前，建議先點擊 **Preview export**。

![Export preview](images/export-preview.png)

Preview 可協助確認：

- Target 數量
- 輸出路徑
- Resolved / unresolved metadata 狀態
- Warning
- 匯出 key 是否正確

範例：

~~~text
Preview targets: 2; warnings: 0
- 0005-test: [Generated] ... (resolved) -> output/0005-test.png
- 0006-test: [Generated] ... (resolved) -> output/0006-test.png
~~~

### 9. Export selected PNG metadata

點擊 **Export selected PNG metadata**。

![Export result 1](images/export-result1.png)

每個匯出目標會寫出：

~~~text
{name}.png
{name}.json
~~~

如果啟用 manifest，也會寫出：

~~~text
manifest.json
~~~

![Export result 2](images/export-result2.png)

## 輸出檔案

### PNG

PNG 是實際輸出的圖片。

當 metadata 可用時，PNG 可嵌入生成參數。

### JSON sidecar

JSON sidecar 會保存結構化匯出 payload，包含：

- Export key
- Group name
- Group ID
- Layer IDs
- Manual label
- Sync index
- Image index
- 可用時的 seed
- 可用時的 params snapshot
- 可用時的 A1111 parameters
- Runtime mode 欄位
- Warning list
- Group target 的 child layer summary

### Manifest

可選的 `manifest.json` 是 batch-level 的匯出索引。

## Metadata 與手動模式

在 AI-enabled 模式中，外掛可以使用保存的 metadata snapshot 與 Krita AI Diffusion integration 寫出生成 metadata。

在手動模式中，prompt search 與 AI metadata lookup 會停用。匯出仍可進行，但外掛不會發明不存在的 prompt 或 seed。

這讓輸出保持誠實：

- 有 metadata 就保留
- 沒 metadata 就保持缺失
- 手動匯出仍可使用
- PNG / JSON / manifest 仍可產生

## Civitai Create Post 驗證

![Civitai create post](images/civitai-post.png)

匯出的 PNG 可以上傳到 Civitai 的 create post 畫面。

當生成 metadata 可用時，Civitai 可以讀取 PNG 內嵌參數，並顯示 prompt、negative prompt、圖片預覽，以及 seed、steps、sampler、guidance 等生成設定。

這可以用來確認外掛匯出的 PNG 仍保留外部工具可解析的 metadata。

## 建議用法

- 匯出前先使用 **Preview export**。
- Auto map 後儲存 `.kra`，讓 metadata mapping 持久保存。
- 使用容易理解的 group label 產生檔名。
- Batch 輸出時啟用 **Write manifest**。
- 只有在明確接受 metadata 不完整時才使用 **Allow unresolved export**。

## 授權

本專案採用 MIT License。

## 相關連結

- Krita: https://krita.org/
- Krita GitHub: https://github.com/KDE/krita
- Krita AI Diffusion: https://github.com/Acly/krita-ai-diffusion