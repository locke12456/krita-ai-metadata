# Krita AI Metadata Export

Krita AI Metadata Export は、Krita AI Diffusion で生成されたレイヤーを、各レイヤーに対応する生成 metadata と一緒に書き出すための Krita プラグインです。

生成レイヤーの選択、読みやすい export group の作成、`.kra` ドキュメント内への metadata mapping 保存、export target の preview、PNG と JSON sidecar の出力を Docker UI から行えます。

![Overview](images/overview.png)

## 主な機能

- Krita 内の Docker UI
- Krita AI Diffusion の生成レイヤー metadata を読み取り
- 1 レイヤーまたは複数レイヤーの選択に対応
- 現在の Krita layer selection をプラグイン側の selection に取り込み可能
- 手動 Group label による分かりやすい export 名
- 選択レイヤーから metadata export group への auto mapping
- `.kra` ファイル内への metadata mapping 保存
- synced / inherited、unsynced、visible、hidden、groups、layers の表示フィルター
- resolved / unresolved export target を確認できる preview panel
- 利用可能な場合、生成 metadata を PNG に埋め込み
- 完全な metadata backup 用 JSON sidecar
- 必要に応じて batch `manifest.json` を出力

## このプラグインの目的

Krita AI Diffusion は画像と metadata を生成できますが、レイヤーを編集、グループ化、リネーム、コピー、または後から batch export する場合、生成 metadata と実際のレイヤーの対応が失われやすくなります。

このプラグインは Krita project 向けの専用 metadata export workflow を追加し、整理後の AI 生成レイヤーでも prompt、seed、関連 metadata を正しく書き出せるようにします。

## 必要環境

- Krita
- Krita AI Diffusion
- Krita Python plugin support

## インストール

1. この repository をダウンロード、または clone します。
2. プラグインフォルダを Krita の Python plugin directory にコピーします。
3. Krita を再起動します。
4. Krita の Python Plugin Manager でプラグインを有効化します。
5. Krita の Docker menu から Metadata Export docker を開きます。

## 基本ワークフロー

![Layout](images/layout.png)

### 1. Krita で画像を生成、または既存ファイルを開く

通常通り Krita AI Diffusion を使用します。

生成レイヤーには、次のような metadata が含まれることがあります。

~~~text
[Generated] 1girl, chibi,
wariza,
very long hair, big eyes, animal ear fluff, animal ears,
white hair, blue eyes,
maid apron, (1008361379)
~~~

### 2. Metadata Export docker を開く

Docker には次の情報が表示されます。

- 現在の document 状態
- 選択中の layer 数
- Layer metadata list
- Metadata sync 状態
- Group label 入力欄
- Output folder
- Export mode
- Manifest と export options
- Preview と export result log

![Docker Main](images/overview.png)

### 3. Layer 表示フィルターを設定する

Docker 上部の checkbox で、layer list に表示する項目を制御できます。

- **Synced / inherited**
- **Unsynced**
- **Visible**
- **Hidden**
- **Groups**
- **Layers**

生成画像レイヤー、通常の paint layer、background layer が混在している document で、export target を探しやすくなります。

### 4. 現在の Krita selection を取り込む

**Import current Krita selection** をクリックすると、現在 Krita で選択している layer をプラグイン側の selection に反映できます。

Docker には選択数が表示されます。

~~~text
Selected layers: 1
~~~

または：

~~~text
Selected layers: 4
~~~

### 5. Group label を入力する

Auto mapping を行う前に、人間が読みやすい group label を入力します。

例：

~~~text
chibi
~~~

プラグインは次のような export 名を作成します。

~~~text
[0001] - chibi
0001-chibi.png
0001-chibi.json
~~~

複数レイヤーを選択した場合、連番の target が作成されます。

~~~text
0001-chibi.png
0002-chibi.png
0003-chibi.png
0004-chibi.png
~~~

Seed は metadata 内に保存されますが、group name や filename には使用されません。

### 6. Auto map selected layers

**Auto map selected layers** をクリックします。

Auto mapping は metadata export group を作成し、その mapping を `.kra` document に保存します。

![Auto Map](images/auto-map.png)

Mapping 後、選択した生成レイヤーは次のような export group の下に表示されます。

~~~text
[0001] - chibi
  [Generated] 1girl, chibi,
  wariza,
  ...
~~~

### 7. Output folder を選択する

現在の document が保存済みの場合、output folder は既定で `.kra` の保存場所に同期されます。

例：

~~~text
E:\code\dev\AI\productions\games\ero\pixel\plugin test\release\test
~~~

現在の document が未保存の場合、home export folder が使用されます。

~~~text
C:\Users\L\krita_ai_metadata_export
~~~

Cross-platform 表記では次の通りです。

~~~text
~/krita_ai_metadata_export
~~~

**Browse** をクリックして手動で output folder を選択することもできます。

### 8. Export options を設定する

現在の options には次のものがあります。

- **Export mode**
  - `Selected docker layers`
- **Overwrite existing files**
- **Allow unresolved export**
- **Write manifest**
- **Include invisible selected targets**

現在の主な出力形式は PNG です。JPEG、DPI、resize options は将来の機能として予約されています。

### 9. Export target を preview する

実際にファイルを書き出す前に、**Preview export** をクリックして target と metadata 状態を確認します。

Preview には target 数と warning 数が表示されます。

例：

~~~text
Preview targets: 1; warnings: 0
- 0001-chibi: [Generated] 1girl, chibi,
wariza,
very long hair, big eyes, animal ear fluff, animal ears,
white hair, blue eyes,
maid apron, (1008361379) (resolved) -> C:\Users\L\krita_ai_metadata_export\0001-chibi.png
~~~

![Export Preview](images/export-preview.png)

### 10. PNG metadata を export する

**Export selected PNG metadata** をクリックします。

1 target の場合、結果は次のようになります。

~~~text
Exported: 1; skipped: 0; warnings: 0
- 0001-chibi: C:\Users\L\krita_ai_metadata_export\0001-chibi.png
~~~

4 つの selected targets の場合、結果は次のようになります。

~~~text
Exported: 4; skipped: 0; warnings: 0
- 0001-chibi: E:\...\test\0001-chibi.png
- 0002-chibi: E:\...\test\0002-chibi.png
- 0003-chibi: E:\...\test\0003-chibi.png
- 0004-chibi: E:\...\test\0004-chibi.png
~~~

![Export Result](images/export-result.png)

## Exported Files

各 resolved target について、次のファイルが出力されます。

~~~text
{name}.png
{name}.json
~~~

**Write manifest** が有効な場合、次のファイルも出力されます。

~~~text
manifest.json
~~~

出力例：

~~~text
0001-chibi.json
0001-chibi.png
manifest.json
~~~

PNG には、利用可能な場合、生成 metadata が埋め込まれます。

JSON sidecar には、backup や外部 workflow のために完全な metadata payload が保存されます。

## Civitai Create Post での確認

![Civitai Create Post](images/civitai-post.png)

Export された PNG metadata は、Civitai の create post 画面で読み取ることができます。

Export した PNG を Civitai create post にアップロードすると、Civitai は generation prompt、negative prompt、image preview、および次のような generation parameters を表示できます。

~~~text
Guidance: 5.5
Steps: 30
Sampler: Euler beta
Seed: 1959819091
~~~

Civitai 画面では、次のような prompt が読み取れます。

~~~text
1girl, chibi, wariza, very long hair, big eyes, animal ear fluff, animal ears,
white hair, blue eyes, maid apron, anime, source anime, illustration,
very aesthetic, high resolution, ultra-detailed flat colors, ...
~~~

Metadata 内の resource 名が Civitai 上の model と一致しない場合、Civitai は resource matching warning を表示することがあります。

例：

~~~text
The following resources could not be matched to models on Civitai:
[Illustrious] dvine 2.0
~~~

これは、export された PNG に Civitai create post が解析できる prompt metadata が保持されていることを確認するものです。

## Metadata の保存

このプラグインは export metadata mapping を `.kra` document 内に保存します。

そのため、mapping 作成後に `.kra` を保存していれば、Krita AI Diffusion の job history が削除された後でも、`.kra` 内の metadata snapshot から export metadata を復元できます。

利用可能な metadata snapshot が存在しない場合、その target は unresolved として表示されます。プラグインが prompt、seed、sampler、job 情報を勝手に生成することはありません。

## Notes

- Export 前に **Preview export** で target name と metadata resolution を確認することを推奨します。
- Batch-level index が必要な場合は、**Write manifest** を有効にしてください。
- Metadata が不完全な target を意図的に出力する場合のみ、**Allow unresolved export** を有効にしてください。
- 現在、このプラグインは PNG metadata export を中心にしています。

## Links

- Krita: https://krita.org/
- Krita GitHub: https://github.com/KDE/krita
- Krita AI Diffusion: https://github.com/Acly/krita-ai-diffusion