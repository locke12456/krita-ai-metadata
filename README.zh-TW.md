# Krita AI Metadata Export

Krita AI Metadata Export 是一個 Krita 外掛，用來匯出 Krita AI Diffusion 產生的圖層，並保留每個圖層對應的生成 metadata。

它可以協助你選取生成圖層、建立可讀性高的匯出群組、將 metadata mapping 保存到 `.kra` 文件中、預覽匯出目標，並輸出帶有 metadata 的 PNG 與對應的 JSON sidecar。

![Overview](images/overview.png)

## 功能特色

- Krita 內建 Docker 操作介面
- 讀取 Krita AI Diffusion 生成圖層中的 metadata
- 支援單一圖層與多圖層選取
- 可將目前 Krita 的圖層 selection 匯入外掛 selection
- 使用手動 Group label 建立可讀性高的匯出名稱
- 可自動將選取圖層 mapping 到 metadata export group
- 將 metadata mapping 長期保存於 `.kra` 文件中
- 支援 synced / inherited、unsynced、visible、hidden、groups、layers 顯示篩選
- Preview panel 可檢查 resolved / unresolved 匯出目標
- 可在 PNG 中嵌入生成 metadata
- 匯出完整 JSON sidecar 作為備份
- 可選擇輸出 batch `manifest.json`

## 為什麼需要這個外掛

Krita AI Diffusion 可以產生圖片與 metadata，但當圖層被編輯、分組、重新命名、複製，或之後才要批次匯出時，原始生成資訊很容易和實際圖層失去對應。

這個外掛提供一個專門的 metadata export workflow，讓 Krita 專案中的 AI 生成圖層在整理後仍能正確匯出 prompt、seed 與相關 metadata。

## 系統需求

- Krita
- Krita AI Diffusion
- Krita Python plugin 支援

## 安裝方式

1. 下載或 clone 此 repository。
2. 將外掛資料夾複製到 Krita 的 Python plugin 目錄。
3. 重新啟動 Krita。
4. 在 Krita 的 Python Plugin Manager 啟用外掛。
5. 從 Krita 的 Docker menu 開啟 Metadata Export docker。

## 基本使用流程

![Layout](images/layout.png)

### 1. 在 Krita 中產生或開啟作品

照常使用 Krita AI Diffusion 產生圖片。

生成圖層中可能包含類似以下 metadata：

~~~text
[Generated] 1girl, chibi,
wariza,
very long hair, big eyes, animal ear fluff, animal ears,
white hair, blue eyes,
maid apron, (1008361379)
~~~

### 2. 開啟 Metadata Export docker

Docker 會顯示：

- 目前文件狀態
- 已選取圖層數量
- 圖層 metadata 清單
- Metadata sync 狀態
- Group label 輸入欄位
- Output folder
- Export mode
- Manifest 與匯出選項
- Preview 與 export result log

![Docker Main](images/overview.png)

### 3. 設定圖層顯示篩選

Docker 上方的 checkbox 可控制圖層清單中顯示哪些項目：

- **Synced / inherited**
- **Unsynced**
- **Visible**
- **Hidden**
- **Groups**
- **Layers**

當文件同時包含生成圖層、一般繪圖圖層與背景圖層時，這些篩選可以協助你快速找到要匯出的目標。

### 4. 匯入目前 Krita selection

點擊 **Import current Krita selection**，可以把 Krita 目前選取的圖層同步到外掛 selection。

Docker 會顯示目前選取數量，例如：

~~~text
Selected layers: 1
~~~

或：

~~~text
Selected layers: 4
~~~

### 5. 輸入 Group label

在自動建立 metadata group 前，請先輸入一個人工可讀的 group label。

範例：

~~~text
chibi
~~~

外掛會建立類似以下匯出名稱：

~~~text
[0001] - chibi
0001-chibi.png
0001-chibi.json
~~~

如果選取多個圖層，會建立連號 target：

~~~text
0001-chibi.png
0002-chibi.png
0003-chibi.png
0004-chibi.png
~~~

Seed 會保留在 metadata 裡，但不會用於 group name 或檔名。

### 6. Auto map selected layers

點擊 **Auto map selected layers**。

Auto mapping 會建立 metadata export group，並將 mapping 寫入 `.kra` 文件。

![Auto Map](images/auto-map.png)

Mapping 後，選取的生成圖層會出現在匯出群組底下，例如：

~~~text
[0001] - chibi
  [Generated] 1girl, chibi,
  wariza,
  ...
~~~

### 7. 選擇輸出資料夾

如果目前文件已儲存，輸出資料夾會預設同步到 `.kra` 所在位置。

範例：

~~~text
E:\code\dev\AI\productions\games\ero\pixel\plugin test\release\test
~~~

如果目前文件尚未儲存，外掛會使用 home export folder：

~~~text
C:\Users\L\krita_ai_metadata_export
~~~

跨平台表示方式為：

~~~text
~/krita_ai_metadata_export
~~~

你也可以點擊 **Browse** 手動選擇輸出資料夾。

### 8. 設定匯出選項

目前可用選項包含：

- **Export mode**
  - `Selected docker layers`
- **Overwrite existing files**
- **Allow unresolved export**
- **Write manifest**
- **Include invisible selected targets**

目前主要輸出格式為 PNG。JPEG、DPI、resize 選項是未來預留功能。

### 9. 預覽匯出目標

點擊 **Preview export**，可以在真正寫出檔案前檢查 target 與 metadata 狀態。

Preview 會顯示目標數量與 warning 數量。

範例：

~~~text
Preview targets: 1; warnings: 0
- 0001-chibi: [Generated] 1girl, chibi,
wariza,
very long hair, big eyes, animal ear fluff, animal ears,
white hair, blue eyes,
maid apron, (1008361379) (resolved) -> C:\Users\L\krita_ai_metadata_export\0001-chibi.png
~~~

![Export Preview](images/export-preview.png)

### 10. 匯出 PNG metadata

點擊 **Export selected PNG metadata**。

單一 target 的結果可能如下：

~~~text
Exported: 1; skipped: 0; warnings: 0
- 0001-chibi: C:\Users\L\krita_ai_metadata_export\0001-chibi.png
~~~

四個 selected targets 的結果可能如下：

~~~text
Exported: 4; skipped: 0; warnings: 0
- 0001-chibi: E:\...\test\0001-chibi.png
- 0002-chibi: E:\...\test\0002-chibi.png
- 0003-chibi: E:\...\test\0003-chibi.png
- 0004-chibi: E:\...\test\0004-chibi.png
~~~

![Export Result](images/export-result.png)

## 匯出檔案

每個 resolved target 會輸出：

~~~text
{name}.png
{name}.json
~~~

如果啟用 **Write manifest**，還會輸出：

~~~text
manifest.json
~~~

範例輸出：

~~~text
0001-chibi.json
0001-chibi.png
manifest.json
~~~

PNG 會在可用時嵌入生成 metadata。

JSON sidecar 則保存完整 metadata payload，作為備份與外部工作流程使用。

## Civitai Create Post 驗證

![Civitai Create Post](images/civitai-post.png)

匯出的 PNG metadata 可以被 Civitai 的 create post 畫面讀取。

將匯出的 PNG 上傳到 Civitai create post 後，Civitai 可以顯示生成 prompt、negative prompt、圖片預覽，以及以下生成參數：

~~~text
Guidance: 5.5
Steps: 30
Sampler: Euler beta
Seed: 1959819091
~~~

Civitai 畫面中可讀到類似以下 prompt：

~~~text
1girl, chibi, wariza, very long hair, big eyes, animal ear fluff, animal ears,
white hair, blue eyes, maid apron, anime, source anime, illustration,
very aesthetic, high resolution, ultra-detailed flat colors, ...
~~~

如果 metadata 中的 resource 名稱無法對應到 Civitai 上的 model，Civitai 也可能顯示 resource matching warning。

範例：

~~~text
The following resources could not be matched to models on Civitai:
[Illustrious] dvine 2.0
~~~

這代表外掛匯出的 PNG 確實保留了 Civitai create post 可以解析的 prompt metadata。

## Metadata 保存方式

外掛會將 export metadata mapping 保存到 `.kra` 文件中。

這代表只要你在建立 mapping 後有儲存 `.kra`，即使 Krita AI Diffusion 的 job history 被刪除，之後仍然可以從 `.kra` 中解析 export metadata。

如果沒有可用的 metadata snapshot，target 會被標記為 unresolved。外掛不會自行發明 prompt、seed、sampler 或 job 資訊。

## 注意事項

- 建議先使用 **Preview export** 確認 target name 與 metadata resolution，再進行匯出。
- 需要批次索引時，請啟用 **Write manifest**。
- 只有在你確定要輸出 metadata 不完整的 target 時，才啟用 **Allow unresolved export**。
- 目前外掛主要聚焦於 PNG metadata export。

## 相關連結

- Krita: https://krita.org/
- Krita GitHub: https://github.com/KDE/krita
- Krita AI Diffusion: https://github.com/Acly/krita-ai-diffusion