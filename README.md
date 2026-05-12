# Invoice OCR Web

一个面向财务内部使用的图片发票 OCR 小系统。用户上传已用颜色框标注的发票图片，系统按相同颜色分组识别含税金额和税费，支持人工编辑、新增或删除明细行，并导出 Excel。

## 功能

- 支持 `png`、`jpg`、`jpeg` 图片上传
- 自动检测彩色框选区域
- 按相似颜色自动分组
- OCR 识别金额和 VAT/税费
- 页面内编辑、新增、删除明细行
- 自动重新计算颜色组汇总和总计
- 保存历史记录到 SQLite
- 导出 Excel，包含 `汇总` 和 `明细` 两个 Sheet
- Docker Compose 部署

## 部署

服务器需要先安装 Docker 和 Docker Compose。

复制环境变量模板：

```bash
cp .env.example .env
```

按需修改 `.env`：

```bash
APP_PORT=8080
MAX_UPLOAD_MB=25
ACCESS_TOKEN=your-token
```

启动：

```bash
docker compose up -d --build
```

访问：

```text
http://服务器IP:8080
```

如果配置了 `ACCESS_TOKEN`，打开页面后在“访问口令”中填写同样的值。

## 本地开发

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 数据目录

运行数据挂载在：

```text
storage/
  db/       SQLite 数据库
  uploads/  临时上传图片
  exports/  导出的 Excel
```

历史结果保存在 SQLite 中。上传图片和导出文件目前不会自动清理，可后续增加定时清理任务。

## 当前范围

第一版只支持图片。PDF 上传、手动画框、固定财务模板填充、账号权限等功能留到后续迭代。
