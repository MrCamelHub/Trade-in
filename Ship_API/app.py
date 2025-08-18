"""
Ship_API Flask 웹 서버
샵바이 API → 코너로지스 API 자동 주문 전송 서비스
"""

import os
import asyncio
import json
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    """서비스 메인 페이지"""
    return jsonify({
        "service": "Bonibello Ship API",
        "version": "2.0",
        "description": "샵바이 API → 코너로지스 API 자동 주문 전송",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/run-shopby": "Manual run Shopby order fetch",
            "/run-cornerlogis": "Manual run Cornerlogis upload",
            "/run-full": "Manual run full workflow",
            "/test": "Test workflow",
            "/status": "Service status",
            "/schedule": "Check schedule condition"
        },
        "schedule": {
            "shopby": "평일 13:00 KST - 샵바이 주문 조회",
            "cornerlogis": "평일 13:30 KST - 코너로지스 업로드"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """헬스체크 엔드포인트"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ship-api"
    })

@app.route('/status')
def status():
    """서비스 상태 확인"""
    try:
        from main import should_run_shopby_now_kst, should_run_cornerlogis_now_kst
        from config import load_app_config
        
        config = load_app_config()
        should_run_shopby = should_run_shopby_now_kst()
        should_run_cornerlogis = should_run_cornerlogis_now_kst()
        
        return jsonify({
            "service": "ship-api",
            "timestamp": datetime.now().isoformat(),
            "schedule": {
                "should_run_shopby_now": should_run_shopby,
                "should_run_cornerlogis_now": should_run_cornerlogis
            },
            "config": {
                "shopby_api_url": config.shopby.base_url,
                "cornerlogis_api_url": config.cornerlogis.base_url,
                "data_dir": str(config.data_dir),
                "has_shopby_credentials": bool(config.shopby.client_id and config.shopby.client_secret),
                "has_cornerlogis_api_key": bool(config.cornerlogis.api_key),
                "has_google_credentials": os.path.exists("youtube-crawling-457503-4fae546ec5fc.json")
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-shopby', methods=['POST'])
def run_shopby():
    """샵바이 주문 조회 수동 실행"""
    try:
        from main import process_shopby_orders
        result = asyncio.run(process_shopby_orders())
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-cornerlogis', methods=['POST'])
def run_cornerlogis():
    """코너로지스 업로드 수동 실행"""
    try:
        from main import process_cornerlogis_upload
        result = asyncio.run(process_cornerlogis_upload())
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-full', methods=['POST'])
def run_full():
    """전체 워크플로우 수동 실행"""
    try:
        from main import run_full_workflow
        result = asyncio.run(run_full_workflow())
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test')
def test():
    """워크플로우 테스트"""
    try:
        from main import test_connections
        result = asyncio.run(test_connections())
        return jsonify({
            "status": "test_completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug-shopby')
def debug_shopby():
    """샵바이 API 디버깅"""
    try:
        import asyncio
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient
        
        async def debug_headers():
            config = load_app_config()
            
            debug_info = {
                "config": {
                    "base_url": config.shopby.base_url,
                    "system_key": config.shopby.system_key[:20] + "...",
                    "auth_token": config.shopby.auth_token[:50] + "...",
                    "version": config.shopby.version
                },
                "env_vars": {
                    "SHOPBY_API_BASE_URL": os.getenv("SHOPBY_API_BASE_URL"),
                    "SHOPBY_SYSTEM_KEY": os.getenv("SHOPBY_SYSTEM_KEY", "")[:20] + "..." if os.getenv("SHOPBY_SYSTEM_KEY") else None,
                    "SHOPBY_AUTH_TOKEN": os.getenv("SHOPBY_AUTH_TOKEN", "")[:50] + "..." if os.getenv("SHOPBY_AUTH_TOKEN") else None,
                    "SHOPBY_API_VERSION": os.getenv("SHOPBY_API_VERSION")
                }
            }
            
            # 헤더 생성 테스트
            async with ShopbyApiClient(config.shopby) as client:
                headers = client._get_headers()
                debug_info["headers"] = headers
                
                try:
                    # 간단한 API 호출 시도
                    orders = await client.get_all_pay_done_orders(days_back=1)
                    debug_info["api_call"] = "success"
                    debug_info["orders_count"] = len(orders) if orders else 0
                except Exception as api_error:
                    debug_info["api_call"] = "failed"
                    debug_info["api_error"] = str(api_error)
            
            return debug_info
        
        result = asyncio.run(debug_headers())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/diag-httpbin')
def diag_httpbin():
    """Railway에서 실제 전송되는 헤더/요청을 httpbin으로 에코해서 확인"""
    try:
        import asyncio
        import aiohttp
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient

        async def run():
            config = load_app_config()
            async with ShopbyApiClient(config.shopby) as client:
                headers = client._get_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get("https://httpbin.org/anything", headers=headers) as resp:
                    text = await resp.text()
                    try:
                        data = await resp.json()
                    except Exception:
                        data = None
                    return {
                        "status": resp.status,
                        "text": text,
                        "json": data
                    }

        result = asyncio.run(run())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/shopby-raw')
def shopby_raw():
    """Shopby 주문 조회를 원시 형태로 호출해 응답 상태/본문을 반환"""
    try:
        import asyncio
        import aiohttp
        from datetime import datetime, timedelta
        import pytz
        from urllib.parse import urlencode, quote
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient

        async def run():
            config = load_app_config()
            kst = pytz.timezone("Asia/Seoul")
            end_dt = datetime.now(kst)
            start_dt = end_dt - timedelta(days=1)
            params = {
                "startYmdt": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "endYmdt": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "orderRequestTypes": "PAY_DONE",
            }
            async with ShopbyApiClient(config.shopby) as client:
                headers = client._get_headers()
            base_url = f"{config.shopby.base_url}/orders"
            full_url = f"{base_url}?{urlencode(params, quote_via=quote)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, headers=headers) as resp:
                    text = await resp.text()
                    try:
                        data = await resp.json()
                    except Exception:
                        data = None
                    return {
                        "url": full_url,
                        "status": resp.status,
                        "text": text,
                        "json": data
                    }

        result = asyncio.run(run())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-new-token', methods=['POST'])
def get_new_token():
    """Railway IP에서 새로운 샵바이 토큰 발급"""
    try:
        import asyncio
        import aiohttp
        import json
        
        async def request_new_token():
            token_data = {
                "code": "urezDTa3xw6c",
                "grant_type": "authorization_code", 
                "client_secret": "WtecrihxmAz3Lu3uvAnzrw9PN4i1Cocc",
                "redirect_uri": "https://bonibello.re-hi.co.kr",
                "client_id": "b1hLbVFoS1lUeUZIM0QrZTNuNklUQT09"
            }
            
            headers = {
                "Version": "1.0",
                "Content-Type": "application/json"
            }
            
            url = "https://server-api.e-ncp.com/auth/token/long-lived"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        url,
                        headers=headers,
                        json=token_data
                    ) as response:
                        response_text = await response.text()
                        
                        result = {
                            "status_code": response.status,
                            "headers_sent": headers,
                            "body_sent": token_data,
                            "url": url,
                            "response_text": response_text
                        }
                        
                        if response.status == 200:
                            try:
                                response_json = json.loads(response_text)
                                result["response_json"] = response_json
                                if "access_token" in response_json:
                                    result["new_access_token"] = response_json["access_token"]
                            except json.JSONDecodeError:
                                result["json_parse_error"] = "Response is not valid JSON"
                        
                        return result
                        
                except Exception as e:
                    return {
                        "error": str(e),
                        "url": url,
                        "headers_sent": headers,
                        "body_sent": token_data
                    }
        
        result = asyncio.run(request_new_token())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/schedule-shopby', methods=['POST'])
def schedule_shopby():
    """스케줄된 샵바이 작업 실행"""
    try:
        from main import scheduled_shopby_run
        result = asyncio.run(scheduled_shopby_run())
        return jsonify({
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/schedule-cornerlogis', methods=['POST'])
def schedule_cornerlogis():
    """스케줄된 코너로지스 작업 실행"""
    try:
        from main import scheduled_cornerlogis_run
        result = asyncio.run(scheduled_cornerlogis_run())
        return jsonify({
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/env')
def debug_env():
    """환경변수 디버깅"""
    config = load_app_config()
    
    return jsonify({
        "shopby": {
            "base_url": config.shopby.base_url,
            "system_key": config.shopby.system_key,
            "auth_token": config.shopby.auth_token,
            "version": config.shopby.version
        },
        "cornerlogis": {
            "base_url": config.cornerlogis.base_url,
            "api_key": config.cornerlogis.api_key if config.cornerlogis.api_key else None
        },
        "timezone": config.timezone,
        "data_dir": config.data_dir,
        "raw_env": {
            "SHOPBY_API_BASE_URL": os.getenv("SHOPBY_API_BASE_URL"),
            "SHOPBY_SYSTEM_KEY": os.getenv("SHOPBY_SYSTEM_KEY"),
            "SHOPBY_AUTH_TOKEN": os.getenv("SHOPBY_AUTH_TOKEN"),
            "SHOPBY_API_VERSION": os.getenv("SHOPBY_API_VERSION"),
            "CORNERLOGIS_API_BASE_URL": os.getenv("CORNERLOGIS_API_BASE_URL"),
            "CORNERLOGIS_API_KEY": os.getenv("CORNERLOGIS_API_KEY"),
            "TZ": os.getenv("TZ")
        }
    })

@app.route('/test-sku-mapping')
def test_sku_mapping():
    """특정 SKU의 매핑과 goodsId 조회 테스트"""
    try:
        from config import load_app_config
        from sku_mapping import get_sku_mapping
        from cornerlogis_api_client import CornerlogisApiClient
        import asyncio
        
        config = load_app_config()
        
        result = {
            "test_sku": "50003453",
            "sku_mapping_step": {},
            "goods_id_step": {},
            "errors": []
        }
        
        # 1단계: SKU 매핑 로드
        print("=== 1단계: SKU 매핑 로드 ===")
        try:
            from sku_mapping import load_sku_mapping_from_sheets
            
            # 상세 디버깅 정보 수집
            print(f"시트 ID: {config.mapping.spreadsheet_id}")
            print(f"탭 이름: {config.mapping.tab_name}")
            print(f"Google 인증 JSON 길이: {len(config.google_credentials_json) if config.google_credentials_json else 0}")
            
            sku_mapping = load_sku_mapping_from_sheets(
                spreadsheet_id=config.mapping.spreadsheet_id,
                tab_name=config.mapping.tab_name,
                google_credentials_json=config.google_credentials_json,
                google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None
            )
            
            # 처음 5개 매핑 샘플 수집
            sample_mappings = dict(list(sku_mapping.items())[:5]) if sku_mapping else {}
            
            result["sku_mapping_step"] = {
                "status": "success",
                "total_mappings": len(sku_mapping),
                "test_sku_found": "50003453" in sku_mapping,
                "test_sku_value": sku_mapping.get("50003453", "NOT_FOUND"),
                "sheet_id": config.mapping.spreadsheet_id,
                "tab_name": config.mapping.tab_name,
                "sample_mappings": sample_mappings,
                "google_auth_length": len(config.google_credentials_json) if config.google_credentials_json else 0
            }
            print(f"SKU 매핑 로드 성공: {len(sku_mapping)}개")
            print(f"50003453 매핑: {sku_mapping.get('50003453', 'NOT_FOUND')}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            result["sku_mapping_step"] = {
                "status": "error",
                "error": str(e),
                "error_detail": error_detail,
                "sheet_id": config.mapping.spreadsheet_id if hasattr(config, 'mapping') else "NOT_FOUND",
                "tab_name": config.mapping.tab_name if hasattr(config, 'mapping') else "NOT_FOUND"
            }
            result["errors"].append(f"SKU 매핑 로드 실패: {str(e)}")
            return jsonify(result)
        
        # 2단계: goodsId 조회
        print("=== 2단계: goodsId 조회 ===")
        try:
            if "50003453" in sku_mapping:
                mapped_code = sku_mapping["50003453"]
                print(f"매핑된 코드로 goodsId 조회: {mapped_code}")
                
                async def test_goods_id():
                    async with CornerlogisApiClient(config.cornerlogis) as client:
                        goods_ids = await client.get_goods_ids([mapped_code])
                        return goods_ids
                
                goods_id_result = asyncio.run(test_goods_id())
                
                result["goods_id_step"] = {
                    "status": "success",
                    "mapped_code": mapped_code,
                    "goods_id_found": mapped_code in goods_id_result,
                    "goods_id": goods_id_result.get(mapped_code, "NOT_FOUND"),
                    "all_results": goods_id_result
                }
                print(f"goodsId 조회 결과: {goods_id_result}")
            else:
                result["goods_id_step"] = {
                    "status": "skipped",
                    "reason": "SKU 매핑에서 50003453을 찾을 수 없음"
                }
        except Exception as e:
            result["goods_id_step"] = {
                "status": "error",
                "error": str(e)
            }
            result["errors"].append(f"goodsId 조회 실패: {str(e)}")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "test_sku": "50003453"
        }), 500

@app.route('/test-goods-id-conversion')
def test_goods_id_conversion():
    """실제 주문 데이터로 goodsId 변환 테스트 (POST 없이)"""
    try:
        import asyncio
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient
        from cornerlogis_api_client import CornerlogisApiClient
        from sku_mapping import get_sku_mapping
        from main import prepare_shopby_order_for_cornerlogis
        
        async def test_conversion():
            config = load_app_config()
            
            # 1. 샵바이 주문 조회
            async with ShopbyApiClient(config.shopby) as shopby_client:
                shopby_orders = await shopby_client.get_pay_done_orders_adaptive(days_back=30, chunk_days=1)
            
            if not shopby_orders:
                return {"error": "처리할 주문이 없습니다"}
            
            # 2. SKU 매핑 로드
            sku_mapping = get_sku_mapping(config)
            
            # 3. 첫 번째 주문으로 goodsId 변환 테스트
            if isinstance(shopby_orders, list) and len(shopby_orders) > 0:
                if isinstance(shopby_orders[0], dict) and 'contents' in shopby_orders[0]:
                    actual_orders = shopby_orders[0]['contents']
                else:
                    actual_orders = shopby_orders
            else:
                actual_orders = shopby_orders
            
            if not actual_orders:
                return {"error": "실제 주문 데이터가 없습니다"}
            
            # 첫 번째 주문 처리
            first_order = actual_orders[0]
            enhanced_order = prepare_shopby_order_for_cornerlogis(first_order)
            
            # 4. 코너로지스 변환 (goodsId 조회 포함)
            async with CornerlogisApiClient(config.cornerlogis) as cornerlogis_client:
                outbound_data_list = await cornerlogis_client.prepare_outbound_data(enhanced_order, sku_mapping)
            
            # 모든 주문에 대해 출고 데이터 생성
            all_outbound_data = []
            order_details = []
            
            for i, order in enumerate(actual_orders):
                enhanced_order = prepare_shopby_order_for_cornerlogis(order)
                async with CornerlogisApiClient(config.cornerlogis) as cornerlogis_client:
                    outbound_data_list = await cornerlogis_client.prepare_outbound_data(enhanced_order, sku_mapping)
                
                order_info = {
                    "order_index": i + 1,
                    "order_no": order.get("orderNo", f"ORDER_{i+1}"),
                    "items_count": len(enhanced_order.get("items", [])),
                    "outbound_data_count": len(outbound_data_list),
                    "outbound_data": outbound_data_list,
                    "enhanced_order_items": enhanced_order.get("items", [])
                }
                order_details.append(order_info)
                all_outbound_data.extend(outbound_data_list)
            
            return {
                "shopby_orders_count": len(actual_orders),
                "sku_mapping_count": len(sku_mapping),
                "total_outbound_data_count": len(all_outbound_data),
                "order_details": order_details,
                "summary": {
                    "total_orders": len(actual_orders),
                    "total_items": sum(order["items_count"] for order in order_details),
                    "total_outbound_items": sum(order["outbound_data_count"] for order in order_details)
                }
            }
        
        result = asyncio.run(test_conversion())
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/logs')
def get_logs():
    """최근 로그 조회"""
    try:
        logs_dir = "data/logs"
        if not os.path.exists(logs_dir):
            return jsonify({"logs": [], "message": "No logs found"})
        
        log_files = []
        for file in os.listdir(logs_dir):
            if file.endswith('.log'):
                file_path = os.path.join(logs_dir, file)
                file_stat = os.stat(file_path)
                log_files.append({
                    "file": file,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
        
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            "logs": log_files[:10],  # 최근 10개 파일
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Railway에서는 PORT 환경변수를 사용
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
