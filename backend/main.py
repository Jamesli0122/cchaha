from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import openpyxl
import oracledb
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

DB_CONFIG = {
    "user": "N",
    "password": "1",
    "host": "127.0.0.1",
    "port": 1521,
    "service_name": "orcl",
}

TABLE = "江阴贷款台账合并1"

FIELDS = [
    "客户名称", "客户类型", "客户所有权类型", "证件号", "客户号",
    "借据号", "借据金额", "借据余额", "执行利率", "罚息利率",
    "放款日期", "到期日期", "结清日期", "投向行业", "用途",
    "担保人", "担保物类型", "担保方式", "贷款名称", "五级分类",
    "首贷客户经理", "首贷客户经理证件", "客户经理", "主管机构",
    "逾期本金", "表内欠息", "表外欠息", "欠息天数", "核销标志",
    "客户地址",
]

SUMMARY_TABLE = "江阴时点贷款汇总表"
SUMMARY_FIELDS = ["客户名称", "证件号码", "Y2022", "Y2023", "Y2024", "Y2025", "Y2026"]

MAX_PAGE_SIZE = 100
MAX_EXPORT_ROWS = 50000

pool: oracledb.ConnectionPool | None = None


def _dsn() -> str:
    return f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['service_name']}"


# 切换到 thick 模式以支持 Oracle 11g（thin 模式仅支持 12c+）
oracledb.init_oracle_client(lib_dir=r"D:\app\cc\product\11.2.0\dbhome_1\BIN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = oracledb.create_pool(
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        dsn=_dsn(),
        min=2,
        max=5,
        increment=1,
    )
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="江阴贷款台账查询", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def _serialize(val):
    """把 Oracle 返回的 Python 类型转为 JSON 可序列化值"""
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val


@app.get("/api/search")
def search(
    q: str = Query(..., description="查询关键词（证件号或客户名称）"),
    type: str = Query("zjh", pattern="^(zjh|khmc)$", description="zjh=证件号, khmc=客户名称"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
):
    if type == "zjh":
        where = "证件号 = :keyword"
    else:
        where = "客户名称 LIKE :keyword"

    binds = {"keyword": q if type == "zjh" else q + "%"}

    # --- count ---
    cnt_sql = f"SELECT COUNT(1) FROM {TABLE} WHERE {where}"
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(cnt_sql, binds)
        total = cur.fetchone()[0]

    if total == 0:
        return {"total": 0, "page": page, "size": size, "rows": []}

    upper = page * size
    lower = (page - 1) * size
    binds["upper"] = upper
    binds["lower"] = lower

    cols = ", ".join(FIELDS)
    data_sql = f"""
        SELECT {cols}
        FROM (
            SELECT t.*, ROWNUM rn
            FROM (
                SELECT * FROM {TABLE}
                WHERE {where}
                ORDER BY 证件号, 放款日期
            ) t
            WHERE ROWNUM <= :upper
        )
        WHERE rn > :lower
    """

    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(data_sql, binds)
        rows = []
        for row in cur:
            rows.append({FIELDS[i]: _serialize(row[i]) for i in range(len(FIELDS))})

    return {"total": total, "page": page, "size": size, "rows": rows}


@app.get("/api/export")
def export(
    q: str = Query(..., description="查询关键词"),
    type: str = Query("zjh", pattern="^(zjh|khmc)$"),
):
    if type == "zjh":
        where = "证件号 = :keyword"
    else:
        where = "客户名称 LIKE :keyword"

    binds = {"keyword": q if type == "zjh" else q + "%"}

    sql = f"""
        SELECT * FROM (
            SELECT a.*, ROWNUM rn
            FROM (
                SELECT * FROM {TABLE}
                WHERE {where}
                ORDER BY 证件号, 放款日期
            ) a
            WHERE ROWNUM <= :max_rows
        )
    """
    binds["max_rows"] = MAX_EXPORT_ROWS

    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, binds)
        rows = cur.fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(FIELDS)
    for row in rows:
        ws.append([_serialize(row[i]) for i in range(len(FIELDS))])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"loan_export_{q}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


# --- 时点贷款汇总表 ---

@app.get("/api/summary")
def summary(
    q: str = Query(..., description="查询关键词"),
    type: str = Query("zjh", pattern="^(zjh|khmc)$"),
):
    if type == "zjh":
        where = "证件号码 = :keyword"
    else:
        where = "客户名称 LIKE :keyword"

    binds = {"keyword": q if type == "zjh" else q + "%"}

    # count
    cnt_sql = f"SELECT COUNT(1) FROM {SUMMARY_TABLE} WHERE {where}"
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(cnt_sql, binds)
        total = cur.fetchone()[0]

    if total == 0:
        return {"total": 0, "rows": []}

    # data
    cols = ", ".join(SUMMARY_FIELDS)
    data_sql = f"""
        SELECT {cols} FROM {SUMMARY_TABLE}
        WHERE {where}
        ORDER BY 证件号码
    """

    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(data_sql, binds)
        rows = []
        for row in cur:
            rows.append({SUMMARY_FIELDS[i]: _serialize(row[i]) for i in range(len(SUMMARY_FIELDS))})

    return {"total": total, "rows": rows}


@app.get("/api/summary/export")
def summary_export(
    q: str = Query(..., description="查询关键词"),
    type: str = Query("zjh", pattern="^(zjh|khmc)$"),
):
    if type == "zjh":
        where = "证件号码 = :keyword"
    else:
        where = "客户名称 LIKE :keyword"

    binds = {"keyword": q if type == "zjh" else q + "%"}

    cols = ", ".join(SUMMARY_FIELDS)
    sql = f"SELECT {cols} FROM {SUMMARY_TABLE} WHERE {where} ORDER BY 证件号码"

    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, binds)
        rows = cur.fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(SUMMARY_FIELDS)
    for row in rows:
        ws.append([_serialize(row[i]) for i in range(len(SUMMARY_FIELDS))])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"summary_export_{q}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


# 托管前端静态页面
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
