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
def index():
    """API 엔드포인트 목록"""
    endpoints = [
        {"path": "/", "method": "GET", "description": "API 엔드포인트 목록"},
        {"path": "/run-shopby", "method": "POST", "description": "샵바이 주문 조회 및 변환"},
        {"path": "/run-cornerlogis", "method": "POST", "description": "코너로지스 출고 업로드"},
        {"path": "/run-full", "method": "POST", "description": "전체 워크플로우 실행 (샵바이 → 코너로지스 → 샵바이 상태 변경)"},
        {"path": "/run-delivery-status-only", "method": "POST", "description": "코너로지스 전송 없이 배송준비중 상태 변경만 처리"},
        {"path": "/test-shopby-delivery-status", "method": "POST", "description": "샵바이 배송준비중 상태 변경 테스트"},
        {"path": "/shopby-raw", "method": "GET", "description": "샵바이 API 원본 응답 확인"},
        {"path": "/health", "method": "GET", "description": "API 상태 확인"}
    ]
    
    return jsonify({
        "message": "Bonibello Ship API",
        "endpoints": endpoints,
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

@app.route('/run-full-test', methods=['POST'])
def run_full_test():
    """테스트 데이터로 전체 워크플로우 실행"""
    try:
        from main import run_full_workflow_test
        result = asyncio.run(run_full_workflow_test())
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

@app.route('/test-cornerlogis-prepare', methods=['POST'])
def test_cornerlogis_prepare():
    """코너로지스 API에 POST하기 직전까지 실행하는 테스트 엔드포인트"""
    try:
        import asyncio
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient
        from cornerlogis_api_client import CornerlogisApiClient
        from sku_mapping import get_sku_mapping
        from main import prepare_shopby_order_for_cornerlogis
        
        async def test_preparation():
            config = load_app_config()
            
            result = {
                "step": "cornerlogis_prepare_test",
                "start_time": datetime.now().isoformat(),
                "config": {
                    "cornerlogis_base_url": config.cornerlogis.base_url,
                    "cornerlogis_api_key": config.cornerlogis.api_key[:10] + "..." if config.cornerlogis.api_key else None,
                    "shopby_base_url": config.shopby.base_url,
                    "mapping_spreadsheet_id": config.mapping.spreadsheet_id,
                    "mapping_tab_name": config.mapping.tab_name
                },
                "steps": {},
                "final_outbound_data": [],
                "errors": []
            }
            
            try:
                # 1단계: 샵바이 주문 조회
                print("=== 1단계: 샵바이 주문 조회 ===")
                async with ShopbyApiClient(config.shopby) as shopby_client:
                    shopby_orders = await shopby_client.get_pay_done_orders_adaptive(days_back=7, chunk_days=1)
                
                result["steps"]["shopby_fetch"] = {
                    "status": "success",
                    "orders_count": len(shopby_orders),
                    "message": f"샵바이에서 {len(shopby_orders)}개 주문 조회 완료"
                }
                print(f"샵바이 주문 조회 완료: {len(shopby_orders)}개")
                
                if not shopby_orders:
                    result["steps"]["shopby_fetch"]["status"] = "warning"
                    result["steps"]["shopby_fetch"]["message"] = "처리할 주문이 없습니다"
                    return result
                
                # 2단계: SKU 매핑 로드
                print("=== 2단계: SKU 매핑 로드 ===")
                sku_mapping = get_sku_mapping(config)
                
                result["steps"]["sku_mapping"] = {
                    "status": "success",
                    "mappings_count": len(sku_mapping),
                    "message": f"SKU 매핑 {len(sku_mapping)}개 로드 완료"
                }
                print(f"SKU 매핑 로드 완료: {len(sku_mapping)}개")
                
                # 3단계: 주문 데이터 변환 및 코너로지스 준비
                print("=== 3단계: 주문 데이터 변환 및 코너로지스 준비 ===")
                
                # 첫 번째 주문으로 테스트
                test_order = shopby_orders[0] if isinstance(shopby_orders, list) else shopby_orders
                
                # 주문 데이터 준비
                enhanced_order = prepare_shopby_order_for_cornerlogis(test_order)
                
                result["steps"]["order_preparation"] = {
                    "status": "success",
                    "original_order": {
                        "order_no": test_order.get("orderNo", "UNKNOWN"),
                        "items_count": len(enhanced_order.get("items", [])),
                        "recipient_name": enhanced_order.get("recipientName", "UNKNOWN"),
                        "recipient_phone": enhanced_order.get("recipientPhone", "UNKNOWN"),
                        "recipient_address": enhanced_order.get("recipientAddress", "UNKNOWN")
                    },
                    "message": "주문 데이터 변환 완료"
                }
                
                # 4단계: 코너로지스 출고 데이터 준비 (POST 직전까지)
                print("=== 4단계: 코너로지스 출고 데이터 준비 ===")
                async with CornerlogisApiClient(config.cornerlogis) as cornerlogis_client:
                    outbound_data_list = await cornerlogis_client.prepare_outbound_data(enhanced_order, sku_mapping)
                
                result["steps"]["cornerlogis_prepare"] = {
                    "status": "success",
                    "outbound_data_count": len(outbound_data_list),
                    "message": f"코너로지스 출고 데이터 {len(outbound_data_list)}개 준비 완료 (POST 직전)"
                }
                
                # 5단계: 최종 출고 데이터 상세 정보
                print("=== 5단계: 최종 출고 데이터 상세 정보 ===")
                for i, outbound_data in enumerate(outbound_data_list):
                    outbound_info = {
                        "index": i + 1,
                        "outbound_id": outbound_data.get("outboundId", "N/A"),
                        "company_order_id": outbound_data.get("companyOrderId", "N/A"),
                        "goods_code": outbound_data.get("goodsCode", "N/A"),
                        "goods_id": outbound_data.get("goodsId", "N/A"),
                        "quantity": outbound_data.get("quantity", 0),
                        "price": outbound_data.get("price", 0),
                        "receiver": {
                            "name": outbound_data.get("receiverName", "N/A"),
                            "price": outbound_data.get("receiverPhone", "N/A"),
                            "address": outbound_data.get("receiverAddress", "N/A"),
                            "zipcode": outbound_data.get("receiverZipcode", "N/A")
                        }
                    }
                    result["final_outbound_data"].append(outbound_info)
                
                result["steps"]["final_data"] = {
                    "status": "success",
                    "message": f"최종 출고 데이터 {len(result['final_outbound_data'])}개 구성 완료"
                }
                
                print(f"코너로지스 API POST 직전까지 모든 준비 완료!")
                print(f"출고 데이터 {len(outbound_data_list)}개 준비됨")
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                result["errors"].append({
                    "step": "unknown",
                    "error": str(e),
                    "traceback": error_detail
                })
                print(f"오류 발생: {str(e)}")
            
            result["end_time"] = datetime.now().isoformat()
            result["status"] = "completed" if not result["errors"] else "failed"
            return result
        
        result = asyncio.run(test_preparation())
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/test-shopby-delivery-status', methods=['POST'])
def test_shopby_delivery_status():
    """샵바이 주문 상태를 배송준비중으로 변경하는 테스트 엔드포인트"""
    try:
        import asyncio
        from config import load_app_config
        from shopby_api_client import ShopbyApiClient
        
        async def test_delivery_status_update():
            config = load_app_config()
            
            result = {
                "step": "shopby_delivery_status_test",
                "start_time": datetime.now().isoformat(),
                "config": {
                    "shopby_base_url": config.shopby.base_url,
                    "shopby_system_key": config.shopby.system_key[:20] + "..." if config.shopby.system_key else None,
                    "shopby_auth_token": config.shopby.auth_token[:50] + "..." if config.shopby.auth_token else None
                },
                "test_results": [],
                "errors": []
            }
            
            try:
                # 1단계: 샵바이에서 최근 주문 조회
                print("=== 1단계: 샵바이 최근 주문 조회 ===")
                async with ShopbyApiClient(config.shopby) as shopby_client:
                    shopby_orders = await shopby_client.get_pay_done_orders_adaptive(days_back=7, chunk_days=1)
                
                if not shopby_orders:
                    result["errors"].append("처리할 주문이 없습니다")
                    return result
                
                print(f"샵바이 주문 조회 완료: {len(shopby_orders)}개")
                
                # 2단계: 각 주문에 대해 배송준비중 상태 변경 테스트
                print("=== 2단계: 배송준비중 상태 변경 테스트 ===")
                
                # 첫 번째 주문으로 테스트
                test_order = shopby_orders[0] if isinstance(shopby_orders, list) else shopby_orders
                order_no = test_order.get("orderNo", "UNKNOWN")
                
                print(f"테스트 주문: {order_no}")
                print(f"주문 데이터 구조: {list(test_order.keys())}")
                
                # 주문 데이터 구조 디버깅
                if "deliveryGroups" in test_order:
                    delivery_groups = test_order["deliveryGroups"]
                    print(f"배송 그룹 수: {len(delivery_groups)}")
                    if delivery_groups:
                        first_group = delivery_groups[0]
                        print(f"첫 번째 배송 그룹 키들: {list(first_group.keys())}")
                        if "orderProducts" in first_group:
                            products = first_group["orderProducts"]
                            print(f"주문 상품 수: {len(products)}")
                            if products:
                                first_product = products[0]
                                print(f"첫 번째 상품 키들: {list(first_product.keys())}")
                                if "orderProductOptions" in first_product:
                                    options = first_product["orderProductOptions"]
                                    print(f"상품 옵션 수: {len(options)}")
                                    if options:
                                        first_option = options[0]
                                        print(f"첫 번째 옵션 키들: {list(first_option.keys())}")
                
                # 2-1단계: 주문 상세 조회를 통해 옵션 번호 추출
                print("2-1. 주문 상세 조회 및 옵션 번호 추출...")
                try:
                    order_detail = await shopby_client.get_order_detail(order_no)
                    print(f"✅ 주문 상세 조회 완료")
                    
                    order_option_nos = []
                    
                    # 방법 1: deliveryGroups에서 찾기
                    delivery_groups = order_detail.get('deliveryGroups', [])
                    if delivery_groups:
                        print(f"📦 deliveryGroups에서 옵션 번호 찾기 (길이: {len(delivery_groups)})")
                        for i, delivery_group in enumerate(delivery_groups):
                            print(f"  배송 그룹 {i+1} 키들: {list(delivery_group.keys())}")
                            
                            order_products = delivery_group.get('orderProducts', [])
                            for j, product in enumerate(order_products):
                                print(f"    상품 {j+1} 키들: {list(product.keys())}")
                                
                                order_options = product.get('orderOptions', [])  # 배송준비중 상태 변경용: orderOptions 사용
                                for k, option in enumerate(order_options):
                                    option_no = option.get('orderOptionNo')  # orderOptionNo 추출
                                    if option_no is not None:
                                        order_option_nos.append(option_no)
                                        print(f"      옵션 {k+1}: {option_no}")
                    
                    # 방법 2: 직접 orderProducts에서 찾기
                    if not order_option_nos:
                        print(f"🔍 deliveryGroups가 없어서 직접 orderProducts에서 찾기")
                        order_products = order_detail.get('orderProducts', [])
                        if order_products:
                            print(f"  orderProducts 길이: {len(order_products)}")
                            for i, product in enumerate(order_products):
                                print(f"    상품 {i+1} 키들: {list(product.keys())}")
                                
                                order_options = product.get('orderOptions', [])  # 배송준비중 상태 변경용: orderOptions 사용
                                for j, option in enumerate(order_options):
                                    option_no = option.get('orderOptionNo')  # orderOptionNo 추출
                                    if option_no is not None:
                                        order_option_nos.append(option_no)
                                        print(f"      옵션 {j+1}: {option_no}")
                    
                    print(f"✅ 옵션 번호 추출 완료: {len(order_option_nos)}개 - {order_option_nos}")
                    
                    if not order_option_nos:
                        print(f"❌ 주문 {order_no}에서 옵션 번호를 찾을 수 없습니다.")
                        result["errors"].append("옵션 번호를 찾을 수 없습니다")
                        return result
                        
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    print(f"❌ 주문 상세 조회 실패: {str(e)}")
                    print(f"상세 오류: {error_detail}")
                    
                    result["test_results"].append({
                        "order_no": order_no,
                        "step": "option_extraction",
                        "status": "failed",
                        "message": f"주문 옵션 번호를 찾을 수 없음: {str(e)}",
                        "extracted_options": [],
                        "error_detail": error_detail
                    })
                    return result
                
                # 2-2단계: 배송준비중 상태 변경 API 호출
                print("2-2. 배송준비중 상태 변경 API 호출...")
                delivery_result = await shopby_client.prepare_delivery(order_option_nos)
                
                test_result = {
                    "order_no": order_no,
                    "step": "delivery_status_update",
                    "extracted_options": order_option_nos,
                    "api_result": delivery_result
                }
                
                if delivery_result["status"] == "success":
                    print(f"✅ 배송준비중 상태 변경 성공: {delivery_result['processed_count']}개 옵션")
                    test_result["status"] = "success"
                    test_result["message"] = f"{delivery_result['processed_count']}개 옵션을 배송준비중 상태로 변경했습니다"
                else:
                    print(f"❌ 배송준비중 상태 변경 실패: {delivery_result['message']}")
                    test_result["status"] = "failed"
                    test_result["message"] = delivery_result["message"]
                    test_result["error"] = delivery_result.get("error", "Unknown error")
                
                result["test_results"].append(test_result)
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                result["errors"].append({
                    "step": "unknown",
                    "error": str(e),
                    "traceback": error_detail
                })
                print(f"오류 발생: {str(e)}")
            
            result["end_time"] = datetime.now().isoformat()
            result["status"] = "completed" if not result["errors"] else "failed"
            return result
        
        result = asyncio.run(test_delivery_status_update())
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
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

@app.route('/schedule')
def check_schedule():
    """스케줄러 상태 확인"""
    try:
        import schedule
        from datetime import datetime
        import pytz
        
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        now_utc = datetime.utcnow()
        
        # 다음 실행 시간 계산
        next_shopby = None
        next_cornerlogis = None
        
        # 오늘 날짜가 평일인지 확인
        is_weekday = now_kst.weekday() < 5  # 0=월요일, 4=금요일
        
        if is_weekday:
            today_13_00_kst = now_kst.replace(hour=13, minute=0, second=0, microsecond=0)
            today_13_30_kst = now_kst.replace(hour=13, minute=30, second=0, microsecond=0)
            
            if now_kst < today_13_00_kst:
                next_shopby = today_13_00_kst.isoformat()
            elif now_kst < today_13_30_kst:
                next_shopby = "오늘 이미 실행됨"
                next_cornerlogis = today_13_30_kst.isoformat()
            else:
                next_shopby = "오늘 이미 실행됨"
                next_cornerlogis = "오늘 이미 실행됨"
        else:
            next_shopby = "주말 - 실행 안함"
            next_cornerlogis = "주말 - 실행 안함"
        
        return jsonify({
            "service": "ship-api-scheduler",
            "timestamp": datetime.now().isoformat(),
            "current_time": {
                "kst": now_kst.isoformat(),
                "utc": now_utc.isoformat()
            },
            "schedule": {
                "shopby": {
                    "time": "13:00 KST (04:00 UTC)",
                    "days": "평일 (월-금)",
                    "next_run": next_shopby,
                    "description": "샵바이 주문 조회"
                },
                "cornerlogis": {
                    "time": "13:30 KST (04:30 UTC)",
                    "days": "평일 (월-금)",
                    "next_run": next_cornerlogis,
                    "description": "코너로지스 업로드"
                }
            },
            "is_weekday": is_weekday,
            "status": "running"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-delivery-status-only', methods=['POST'])
async def run_delivery_status_only():
    """
    코너로지스 전송 없이 배송준비중 상태 변경만 처리
    1. 샵바이 최근 주문 조회
    2. 각 주문의 orderOptionNo 추출
    3. 배송준비중 상태로 변경
    """
    config = load_app_config()
    ensure_data_dirs(config.data_dir)
    
    result = {
        "status": "started",
        "timestamp": datetime.now().isoformat(),
        "start_time": datetime.now().isoformat(),
        "shopby_result": {
            "status": "started",
            "start_time": datetime.now().isoformat(),
            "shopby_orders_count": 0,
            "transformed_orders_count": 0,
            "delivery_status_updated_count": 0,
            "delivery_status_failed_count": 0,
            "errors": [],
            "processed_orders": []
        },
        "end_time": None
    }
    
    try:
        print("=== 배송준비중 상태 변경 전용 워크플로우 실행 ===")
        
        # 1단계: 샵바이 최근 주문 조회
        print("=== 1단계: 샵바이 최근 주문 조회 ===")
        async with ShopbyApiClient(config.shopby) as shopby_client:
            shopby_result = await shopby_client.fetch_recent_orders()
            
            if shopby_result["status"] == "success":
                orders = shopby_result.get("orders", [])
                result["shopby_result"]["shopby_orders_count"] = len(orders)
                print(f"샵바이 주문 조회 완료: {len(orders)}개")
                
                # 2단계: 각 주문의 배송준비중 상태 변경
                print("=== 2단계: 배송준비중 상태 변경 ===")
                
                for i, order in enumerate(orders):
                    order_no = order.get("orderNo", f"ORDER_{i+1}")
                    print(f"주문 {i+1}/{len(orders)} 처리 중: {order_no}")
                    
                    try:
                        # 주문 상세 조회를 통해 orderOptionNo 추출
                        order_detail = await shopby_client.get_order_detail(order_no)
                        order_option_nos = []
                        
                        # orderProducts에서 직접 orderOptions 찾기
                        order_products = order_detail.get('orderProducts', [])
                        if order_products:
                            print(f"  📦 orderProducts에서 orderOptionNo 찾기 (길이: {len(order_products)})")
                            for j, product in enumerate(order_products):
                                print(f"    상품 {j+1}: {product.get('productName', 'UNKNOWN')}")
                                
                                order_options = product.get('orderOptions', [])  # 배송준비중 상태 변경용: orderOptions 사용
                                for k, option in enumerate(order_options):
                                    option_no = option.get('orderOptionNo')  # orderOptionNo 추출
                                    if option_no is not None:
                                        order_option_nos.append(option_no)
                                        print(f"      옵션 {k+1}: {option_no}")
                        
                        if order_option_nos:
                            print(f"  ✅ 추출된 orderOptionNo: {order_option_nos}")
                            
                            # 배송준비중 상태 변경
                            delivery_result = await shopby_client.prepare_delivery(order_option_nos)
                            
                            if delivery_result["status"] == "success":
                                print(f"✅ 주문 {order_no} 배송준비중 상태 변경 성공: {delivery_result['processed_count']}개 옵션")
                                result["shopby_result"]["delivery_status_updated_count"] += 1
                                result["shopby_result"]["processed_orders"].append({
                                    "orderNo": order_no,
                                    "status": "success",
                                    "message": f"{delivery_result['processed_count']}개 옵션을 배송준비중 상태로 변경했습니다",
                                    "processed_options": delivery_result["processed_count"],
                                    "extracted_options": order_option_nos
                                })
                            else:
                                print(f"❌ 주문 {order_no} 배송준비중 상태 변경 실패: {delivery_result['message']}")
                                result["shopby_result"]["delivery_status_failed_count"] += 1
                                result["shopby_result"]["processed_orders"].append({
                                    "orderNo": order_no,
                                    "status": "failed",
                                    "message": delivery_result["message"],
                                    "error": delivery_result.get("error", "Unknown error"),
                                    "extracted_options": order_option_nos
                                })
                        else:
                            print(f"⚠️ 주문 {order_no}에서 주문 옵션 번호를 찾을 수 없습니다.")
                            result["shopby_result"]["processed_orders"].append({
                                "orderNo": order_no,
                                "status": "skipped",
                                "message": "주문 옵션 번호를 찾을 수 없음",
                                "extracted_options": []
                            })
                            
                    except Exception as e:
                        print(f"❌ 주문 {order_no} 처리 중 오류: {str(e)}")
                        result["shopby_result"]["errors"].append({
                            "order_no": order_no,
                            "error": str(e)
                        })
                        result["shopby_result"]["processed_orders"].append({
                            "orderNo": order_no,
                            "status": "error",
                            "message": f"처리 중 오류: {str(e)}",
                            "extracted_options": []
                        })
                    
                    # API 호출 간격 조절
                    if i < len(orders) - 1:
                        await asyncio.sleep(1)
                
                result["shopby_result"]["status"] = "completed"
                result["shopby_result"]["end_time"] = datetime.now().isoformat()
                result["status"] = "completed"
                result["end_time"] = datetime.now().isoformat()
                
                print("=== 배송준비중 상태 변경 완료 ===")
                print(f"성공: {result['shopby_result']['delivery_status_updated_count']}개 주문")
                print(f"실패: {result['shopby_result']['delivery_status_failed_count']}개 주문")
                print(f"건너뜀: {len([o for o in result['shopby_result']['processed_orders'] if o['status'] == 'skipped'])}개 주문")
                
            else:
                error_msg = f"샵바이 주문 조회 실패: {shopby_result.get('message', 'Unknown error')}"
                print(error_msg)
                result["shopby_result"]["status"] = "failed"
                result["shopby_result"]["errors"].append(error_msg)
                result["status"] = "failed"
                result["end_time"] = datetime.now().isoformat()
        
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f"배송준비중 상태 변경 워크플로우 중 치명적 오류: {str(e)}"
        print(error_msg)
        result["status"] = "failed"
        result["shopby_result"]["status"] = "failed"
        result["shopby_result"]["errors"].append(error_msg)
        result["end_time"] = datetime.now().isoformat()
        
        return jsonify({
            "status": "error",
            "message": error_msg,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # 스케줄러 초기화 및 시작
    import schedule
    import threading
    import time
    from datetime import datetime
    import pytz
    
    def run_shopby_schedule():
        """13:00 KST에 샵바이 주문 조회 실행"""
        try:
            print(f"[{datetime.now().isoformat()}] 🕐 13:00 KST 스케줄 실행: 샵바이 주문 조회")
            from main import process_shopby_orders
            result = asyncio.run(process_shopby_orders())
            print(f"[{datetime.now().isoformat()}] ✅ 13:00 KST 스케줄 완료: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] ❌ 13:00 KST 스케줄 오류: {str(e)}")
    
    def run_cornerlogis_schedule():
        """13:30 KST에 코너로지스 업로드 실행"""
        try:
            print(f"[{datetime.now().isoformat()}] 🕐 13:30 KST 스케줄 실행: 코너로지스 업로드")
            from main import process_cornerlogis_upload
            result = asyncio.run(process_cornerlogis_upload())
            print(f"[{datetime.now().isoformat()}] ✅ 13:30 KST 스케줄 완료: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] ❌ 13:30 KST 스케줄 오류: {str(e)}")
    
    def start_scheduler():
        """백그라운드에서 스케줄러 실행"""
        # KST 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        
        # 평일 13:00 KST (UTC 04:00) - 샵바이 주문 조회
        schedule.every().monday.at("04:00").do(run_shopby_schedule)
        schedule.every().tuesday.at("04:00").do(run_shopby_schedule)
        schedule.every().wednesday.at("04:00").do(run_shopby_schedule)
        schedule.every().thursday.at("04:00").do(run_shopby_schedule)
        schedule.every().friday.at("04:00").do(run_shopby_schedule)
        
        # 평일 13:30 KST (UTC 04:30) - 코너로지스 업로드
        schedule.every().monday.at("04:30").do(run_cornerlogis_schedule)
        schedule.every().tuesday.at("04:30").do(run_cornerlogis_schedule)
        schedule.every().wednesday.at("04:30").do(run_cornerlogis_schedule)
        schedule.every().thursday.at("04:30").do(run_cornerlogis_schedule)
        schedule.every().friday.at("04:30").do(run_cornerlogis_schedule)
        
        print(f"[{datetime.now().isoformat()}] 🚀 스케줄러 시작됨")
        print(f"[{datetime.now().isoformat()}] 📅 평일 13:00 KST - 샵바이 주문 조회")
        print(f"[{datetime.now().isoformat()}] 📅 평일 13:30 KST - 코너로지스 업로드")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    
    # 백그라운드 스레드에서 스케줄러 시작
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Railway에서는 PORT 환경변수를 사용
    port = int(os.environ.get('PORT', 8000))
    print(f"[{datetime.now().isoformat()}] 🌐 Flask 서버 시작: 포트 {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
