from fastapi import FastAPI, HTTPException, Request
import requests
import uvicorn
import time

app = FastAPI(title="高德路线小助手")

# 你的专属高德 Key 已经注入
AMAP_KEY = "3efc0efe5998f0a97716f6f189fb985d"

# =======================
# 👇 新增：访问日志大喇叭中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n[🚀 收到新请求] 路径: {request.url.path} | 参数: {request.query_params}")
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    print(f"[✅ 请求处理完成] 状态码: {response.status_code} | 耗时: {process_time:.4f}秒")
    return response
# =======================
def get_location(address: str):
    """【步骤1】把中文地名翻译成高德认识的经纬度"""
    url = f"https://restapi.amap.com/v3/geocode/geo?address={address}&key={AMAP_KEY}"
    res = requests.get(url).json()
    if res.get('status') == '1' and res.get('geocodes'):
        return res['geocodes'][0]['location']
    return None

@app.get("/get_route")
def get_route(start: str, end: str):
    """【步骤2】给 Dify 大模型调用的极简接口"""

    start_loc = get_location(start)
    end_loc = get_location(end)

    if not start_loc or not end_loc:
        raise HTTPException(status_code=400, detail="找不到该地点，请大模型提示用户检查输入")

    # 调用高德综合交通规划接口
    # 注意：真实高铁接口权限极高，此处以跨城综合公共交通(含大巴/火车)为例
    route_url = f"https://restapi.amap.com/v3/direction/transit/integrated?origin={start_loc}&destination={end_loc}&city=0558&cityd=021&key={AMAP_KEY}"
    res = requests.get(route_url).json()

    if res.get('status') != '1' or not res.get('route', {}).get('transits'):
        return {"result": "抱歉，高德地图未能找到合适的直达路线。"}

    # 【步骤3】暴力清洗：为大模型省下成千上万的 Token
    best_transit = res['route']['transits'][0]
    cost = best_transit.get('cost', '未知')
    duration_min = int(best_transit.get('duration', 0)) // 60

    segments = []
    for seg in best_transit.get('segments', []):
        if 'bus' in seg and seg['bus'].get('buslines'):
            bus_name = seg['bus']['buslines'][0]['name']
            segments.append(bus_name)

    route_str = " -> ".join(segments)

    # 返回极其干净的数据给 Dify
    return {"result": f"推荐路线：{route_str}。预计耗时 {duration_min} 分钟，总花费约 {cost} 元。"}

if __name__ == "__main__":
    # 启动服务，运行在 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)
