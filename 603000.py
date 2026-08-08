import baostock as bs
import pandas as pd
import matplotlib.pyplot as plt


# 登录
bs.login()


# 获取603000历史日K
rs = bs.query_history_k_data_plus(
    "sh.603000",
    """
    date,
    open,
    high,
    low,
    close,
    volume,
    amount
    """,
    start_date="2024-01-01",
    end_date="2025-01-01",
    frequency="d",
    adjustflag="2"
)


data = []

while rs.next():
    data.append(rs.get_row_data())


# 转DataFrame
df = pd.DataFrame(
    data,
    columns=rs.fields
)


# 数据类型转换
df["close"] = df["close"].astype(float)
df["volume"] = df["volume"].astype(float)

df["date"] = pd.to_datetime(df["date"])


print(df.head())


bs.logout()


# =====================
# 图形展示
# =====================

plt.figure(figsize=(12,6))


# 上半部分：价格
plt.subplot(2,1,1)

plt.plot(
    df["date"],
    df["close"]
)

plt.title("603000.SH Price")
plt.ylabel("Close")


# 下半部分：成交量
plt.subplot(2,1,2)

plt.bar(
    df["date"],
    df["volume"]
)

plt.title("603000.SH Volume")
plt.ylabel("Volume")


plt.xlabel("Date")

plt.tight_layout()

plt.show()