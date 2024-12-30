# Crypto Price Compose

用于获取和计算加密货币价格的API服务。

## 功能特点

- 支持多个交易所的价格查询（Binance、OKX、OKJ）
- 支持Google搜索价格数据
- 提供USDT/JPY汇率计算
- 可配置的价格倍率管理
- 异步处理
- 完整的错误处理和日志记录

## API文档

### 获取USDT/JPY组合计算价格

- 路径: /crypto/compose
- 方法: GET
- 参数:
  - group (查询参数, 可选): 价格倍率分组名称
- 响应: 返回基于BTC价格计算的USDT/JPY汇率，包含价格倍率调整

```json
{
  "usdt_jpy": {
    "bid_price": 157.67,
    "ask_price": 157.76,
    "last_price": 157.7,
    "spread_percent": 0.06
  },
  "usdt_jpy_google": {
    "last_price": 157.55
  },
  "source_data": {
    "btc_usdt": {
      "bid_price": 93862.35,
      "ask_price": 93862.36,
      "last_price": 93862.36,
      "change_percent_24h": -1.353,
      "exchange": "Binance",
      "timestamp": "2024-12-30T14:51:12.295000"
    },
    "btc_jpy": {
      "bid_price": 14799587,
      "ask_price": 14807946,
      "last_price": 14802183,
      "change_percent_24h": -1.46269045601201,
      "exchange": "OKJ",
      "timestamp": "2024-12-30T06:51:05.005Z"
    },
    "btc_jpy_google": {
      "last_price": 14788087.3,
      "exchange": "Google",
      "timestamp": "2024-12-30T14:51:13.698101"
    }
  },
  "calculation_time": "2024-12-30T14:51:12.295000",
  "power_multiplier": 1
}
```

### 价格倍率配置接口

#### 获取所有价格计算倍数配置

- 路径: /power/configs
- 方法: GET
- 响应: 返回所有价格计算倍数配置列表

```json
[
  {
    "id": 1,
    "group": "default",
    "power": 1.01,
    "description": "Default multiplier"
  },
  {
    "id": 2,
    "group": "premium",
    "power": 1.01,
    "description": null
  }
]
```

#### 获取指定组的价格计算倍数配置

- 路径: /power/configs/{group}
-   方法: GET
- 参数:
  - group (路径参数): 配置组名称
- 响应: 返回指定组的价格计算倍数配置

#### 创建新的价格计算倍数配置

- 路径: /power/configs
- 方法: POST
- 请求体:

```json
{
  "group": "new_group",
  "power": 1.01,
  "description": "New multiplier"
}
```

#### 更新指定组的价格计算倍数配置

- 路径: /power/configs/{group}
- 方法: PUT
- 参数:
  - group (路径参数): 配置组名称
- 请求体:

```json
  {
    "group": "string",
    "power": 1.0,
    "description": "string"
  }
```

#### 删除指定组的价格计算倍数配置

- 路径: /power/configs/{group}
- 方法: DELETE
- 参数:
  - group (路径参数): 配置组名称

```json
  {
    "message": "Configuration deleted successfully"
  }
```
#### 批量更新所有配置的power值

- 路径: /power/configs/power/batch
- 方法: PUT
- 请求体:

```json
  {
    "power": 1.01
  }
```

- 说明: 更新所有配置组的power值（必须大于等于0）