from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(title="高德路线小助手")

# 这里填你自己在高德开放平台申请的免费 Key
AMAP_KEY = "3efc0efe5998f0a97716f6f189fb985d" 

def get_location(address: str):
    """把地名翻译成经纬度"""
    url = f"https://restapi.amap.com/v3/geocode/geo?address={address}&key={AMAP_KEY}"
    res = requests.get(url).json()
    if res['status'] == '1' and res['geocodes']:
        return res['geocodes'][0]['location']
    return None

@app.get("/get_transit_route")
def get_transit_route(start: str, end: str):
    """Dify 的大模型只会调用这个极简接口"""
    
    # 1. 查起点经纬度
    start_loc = get_location(start)
    # 2. 查终点经纬度
    end_loc = get_location(end)
    
    if not start_loc or not end_loc:
        raise HTTPException(status_code=400, detail="找不到该地点，请检查输入")

    # 3. 查高德的公交/高铁接口 (以公交接口为例，因为高德的高铁接口权限较严，通常用综合出行接口)
    # 假设城市代码 021 (上海), 0558 (亳州) - 实际应用中这些也需要查API，这里简化演示
    route_url = f"https://restapi.amap.com/v3/direction/transit/integrated?origin={start_loc}&destination={end_loc}&city=0558&cityd=021&key={AMAP_KEY}"
    res = requests.get(route_url).json()
    
    if res['status'] != '1' or not res['route']['transits']:
        return {"result": "抱歉，没有查到合适的直达路线。"}

    # 4. 暴力清洗：把几万行废话变成一句话
    best_transit = res['route']['transits'][0]
    cost = best_transit.get('cost', '未知')
    duration_min = int(best_transit.get('duration', 0)) // 60
    
    segments = []
    for seg in best_transit['segments']:
        if 'bus' in seg and seg['bus']['buslines']:
            bus_name = seg['bus']['buslines'][0]['name']
            segments.append(bus_name)
            
    route_str = " -> ".join(segments)
    
    # 5. 返回极其干净的数据给 Dify
    clean_result = f"推荐路线：{route_str}。预计耗时 {duration_min} 分钟，花费 {cost} 元。"
    return {"result": clean_result}

# 运行命令: uvicorn your_file_name:app --host 0.0.0.0 --port 8000