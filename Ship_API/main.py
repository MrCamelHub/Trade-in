from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import pytz
import holidays

from config import load_app_config, ensure_data_dirs
from shopby_api_client import ShopbyApiClient
from cornerlogis_api_client import CornerlogisApiClient
from data_transformer import ShopbyToCornerlogisTransformer
from sku_mapping import get_sku_mapping
from google_sheets_logger import GoogleSheetsLogger


def prepare_shopby_order_for_cornerlogis(shopby_order: Dict[str, Any]) -> Dict[str, Any]:
    """
    샵바이 API 응답 데이터를 코너로지스 변환에 적합한 형식으로 준비
    """
    # 배송 그룹에서 정보 추출
    delivery_groups = shopby_order.get('deliveryGroups', [])
    if not delivery_groups:
        return shopby_order
    
    delivery_group = delivery_groups[0]
    
    # 상품 정보 추출
    items = []
    for product in delivery_group.get('orderProducts', []):
        for option in product.get('orderProductOptions', []):
            item = {
                'productCode': product.get('productManagementCd'),
                'productManagementCd': product.get('productManagementCd'),
                'productName': product.get('productName'),
                'quantity': option.get('orderCnt', 1),
                'unitPrice': option.get('adjustedAmt', 0),
                'totalPrice': option.get('adjustedAmt', 0),
                'adjustedAmt': option.get('adjustedAmt', 0),
                'salePrice': option.get('salePrice', 0)
            }
            items.append(item)
    
    # 향상된 주문 데이터 구성
    enhanced_order = {
        **shopby_order,
        'recipientName': delivery_group.get('receiverName'),
        'recipientPhone': delivery_group.get('receiverContact1'),
        'deliveryAddress1': delivery_group.get('receiverAddress'),
        'deliveryAddress2': delivery_group.get('receiverDetailAddress'),
        'deliveryZipCode': delivery_group.get('receiverZipCd'),
        'deliveryMemo': delivery_group.get('deliveryMemo'),
        'items': items
    }
    
    return enhanced_order


async def process_shopby_orders() -> Dict[str, Any]:
    """
    샵바이 주문 조회 및 구글시트 기록 (오후 1:00 실행)
    
    Returns:
        처리 결과 딕셔너리
    """
    config = load_app_config()
    ensure_data_dirs(config.data_dir)
    
    result = {
        "start_time": datetime.now().isoformat(),
        "status": "started",
        "shopby_orders_count": 0,
        "transformed_orders_count": 0,
        "cornerlogis_success_count": 0,
        "cornerlogis_failure_count": 0,
        "errors": [],
        "processed_orders": []
    }
    
    try:
        print("=== 샵바이 API 주문 처리 시작 ===")
        
        # 1. 샵바이에서 주문 조회 (먼저 실행)
        print("1. 샵바이 API에서 주문 조회 중...")
        shopby_orders = []
        
        async with ShopbyApiClient(config.shopby) as shopby_client:
            # 우선 단일 범위 조회 시도, 실패 시 자동 청크 폴백
            shopby_orders = await shopby_client.get_pay_done_orders_adaptive(days_back=30, chunk_days=1)
            result["shopby_orders_count"] = len(shopby_orders)
            print(f"샵바이 주문 조회 완료: {len(shopby_orders)}개 주문")
        
        if not shopby_orders:
            print("처리할 주문이 없습니다.")
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            return result
        
        # 2. SKU 매핑 로드 (주문이 있을 때만 실행)
        print("2. SKU 매핑 로드 중...")
        sku_mapping = get_sku_mapping(config)
        print(f"SKU 매핑 로드 완료: {len(sku_mapping)}개 항목")
        
        # 2.5. 구글 시트에 상품 정보 기록 (임시 비활성화)
        print("2.5. 구글 시트에 상품 정보 기록 중... (임시 스킵)")
        print("⚠️ Google 인증 문제로 인해 시트 로깅을 임시로 스킵합니다")
        # try:
        #     sheets_logger = GoogleSheetsLogger(
        #         spreadsheet_id="1pXOIiSCXpEOUHQUgl_4FUDltRG9RYq0_cadJX4Cre1o",
        #         google_credentials_json=config.google_credentials_json,
        #         google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None
        #     )
        #     
        #     # 샵바이 API 응답 구조 처리 (로깅용)
        #     if isinstance(shopby_orders, list) and len(shopby_orders) > 0:
        #         if isinstance(shopby_orders[0], dict) and 'contents' in shopby_orders[0]:
        #             actual_orders_for_logging = shopby_orders[0]['contents']
        #         else:
        #             actual_orders_for_logging = shopby_orders
        #     else:
        #         actual_orders_for_logging = shopby_orders
        #     
        #     # 오늘 날짜로 기록
        #     today_str = datetime.now().strftime("%Y-%m-%d")
        #     sheets_success = sheets_logger.log_shopby_orders(actual_orders_for_logging, today_str)
        #     
        #     if sheets_success:
        #         print("✅ 구글 시트 기록 완료")
        #     else:
        #         print("⚠️ 구글 시트 기록 실패 (처리는 계속)")
        #         
        # except Exception as e:
        #     print(f"⚠️ 구글 시트 기록 오류: {e} (처리는 계속)")
        #     result["errors"].append(f"구글 시트 기록 오류: {str(e)}")
        
        # 3. 데이터 변환
        print("3. 주문 데이터 변환 중...")
        
        # 샵바이 API 응답 구조 처리 (변환용)
        if isinstance(shopby_orders, list) and len(shopby_orders) > 0:
            if isinstance(shopby_orders[0], dict) and 'contents' in shopby_orders[0]:
                # API 응답에서 실제 주문 데이터 추출
                actual_orders_for_transform = shopby_orders[0]['contents']
                print(f"실제 주문 수 추출: {len(actual_orders_for_transform)}개")
            else:
                actual_orders_for_transform = shopby_orders
        else:
            actual_orders_for_transform = shopby_orders
        
        transformer = ShopbyToCornerlogisTransformer(sku_mapping)
        transformed_orders = transformer.transform_orders(actual_orders_for_transform)
        result["transformed_orders_count"] = len(transformed_orders)
        result["shopby_orders_count"] = len(actual_orders_for_transform)  # 실제 주문 수로 업데이트
        print(f"데이터 변환 완료: {len(transformed_orders)}개 주문")
        
        if not transformed_orders:
            print("변환된 주문이 없습니다.")
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            return result
        
        # 4. 샵바이 주문 데이터를 파일로 저장 (1:30에 읽을 수 있도록)
        print("4. 샵바이 주문 데이터 저장 중...")
        await save_shopby_orders(config, actual_orders_for_transform, transformed_orders)
        
        result["status"] = "completed"
        result["end_time"] = datetime.now().isoformat()
        
        print("=== 샵바이 주문 조회 완료 ===")
        print(f"총 샵바이 주문: {result['shopby_orders_count']}")
        print(f"변환된 주문: {result['transformed_orders_count']}")
        print("📄 오후 1:30 코너로지스 업로드를 위해 데이터 저장 완료")
        
        if result["errors"]:
            print(f"오류 수: {len(result['errors'])}")
            for error in result["errors"][:3]:  # 최대 3개만 출력
                print(f"  - {error}")
        
        return result
        
    except Exception as e:
        error_msg = f"전체 처리 중 치명적 오류: {str(e)}"
        print(error_msg)
        result["status"] = "failed"
        result["errors"].append(error_msg)
        result["end_time"] = datetime.now().isoformat()
        return result


async def process_cornerlogis_upload() -> Dict[str, Any]:
    """
    코너로지스 출고 업로드 (오후 1:30 실행)
    1시에 저장된 샵바이 주문 데이터를 읽어서 코너로지스로 전송
    
    Returns:
        처리 결과 딕셔너리
    """
    config = load_app_config()
    ensure_data_dirs(config.data_dir)
    
    result = {
        "start_time": datetime.now().isoformat(),
        "status": "started",
        "cornerlogis_success_count": 0,
        "cornerlogis_failure_count": 0,
        "errors": [],
        "processed_orders": []
    }
    
    try:
        print("=== 코너로지스 출고 업로드 시작 ===")
        
        # 1. 1시에 저장된 샵바이 주문 데이터 로드
        print("1. 샵바이 주문 데이터 로드 중...")
        shopby_orders, sku_mapping = await load_shopby_orders(config)
        
        if not shopby_orders:
            print("업로드할 주문 데이터가 없습니다.")
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            return result
        
        print(f"로드된 주문 수: {len(shopby_orders)}개")
        
        # 2. 코너로지스 API로 전송
        print("2. 코너로지스 API로 주문 전송 중...")
        
        async with CornerlogisApiClient(config.cornerlogis) as cornerlogis_client:
            # 샵바이 API 응답 구조 처리
            if isinstance(shopby_orders, list) and len(shopby_orders) > 0:
                if isinstance(shopby_orders[0], dict) and 'contents' in shopby_orders[0]:
                    # API 응답에서 실제 주문 데이터 추출
                    actual_orders = shopby_orders[0]['contents']
                else:
                    actual_orders = shopby_orders
            else:
                actual_orders = shopby_orders
                
            # 개별 주문 처리
            for i, shopby_order in enumerate(actual_orders):
                order_no = shopby_order.get("orderNo", f"ORDER_{i+1}")
                
                try:
                    print(f"주문 처리 중: {order_no} ({i+1}/{len(actual_orders)})")
                    
                    # 샵바이 주문 데이터를 올바른 형식으로 변환
                    enhanced_order = prepare_shopby_order_for_cornerlogis(shopby_order)
                    
                    # 코너로지스 출고 데이터로 변환
                    outbound_data_list = await cornerlogis_client.prepare_outbound_data(enhanced_order, sku_mapping)
                    
                    if not outbound_data_list:
                        error_msg = f"주문 {order_no}: 변환할 상품이 없습니다"
                        print(error_msg)
                        result["errors"].append(error_msg)
                        result["cornerlogis_failure_count"] += 1
                        continue
                    
                    # 코너로지스 API 호출 (배열로 전송)
                    cornerlogis_result = await cornerlogis_client.create_outbound_order(outbound_data_list)
                    
                    if cornerlogis_result:
                        print(f"주문 {order_no} 처리 성공 ({len(outbound_data_list)}개 상품)")
                        result["cornerlogis_success_count"] += 1
                        result["processed_orders"].append({
                            "orderNo": order_no,
                            "status": "success",
                            "items_count": len(outbound_data_list),
                            "cornerlogis_result": cornerlogis_result
                        })
                    else:
                        error_msg = f"주문 {order_no} 코너로지스 API 호출 실패"
                        print(error_msg)
                        result["errors"].append(error_msg)
                        result["cornerlogis_failure_count"] += 1
                        result["processed_orders"].append({
                            "orderNo": order_no,
                            "status": "failed",
                            "error": "API 호출 실패"
                        })
                    
                    # API 호출 간격 조절
                    if i < len(actual_orders) - 1:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    error_msg = f"주문 {order_no} 처리 중 오류: {str(e)}"
                    print(error_msg)
                    result["errors"].append(error_msg)
                    result["cornerlogis_failure_count"] += 1
                    result["processed_orders"].append({
                        "orderNo": order_no,
                        "status": "error",
                        "error": str(e)
                    })
        
        # 3. 결과 저장
        await save_cornerlogis_result(config, result)
        
        result["status"] = "completed"
        result["end_time"] = datetime.now().isoformat()
        
        print("=== 코너로지스 업로드 완료 ===")
        print(f"코너로지스 전송 성공: {result['cornerlogis_success_count']}")
        print(f"코너로지스 전송 실패: {result['cornerlogis_failure_count']}")
        
        if result["errors"]:
            print(f"오류 수: {len(result['errors'])}")
            for error in result["errors"][:3]:  # 최대 3개만 출력
                print(f"  - {error}")
        
        return result
        
    except Exception as e:
        error_msg = f"코너로지스 업로드 중 치명적 오류: {str(e)}"
        print(error_msg)
        result["status"] = "failed"
        result["errors"].append(error_msg)
        result["end_time"] = datetime.now().isoformat()
        return result


async def save_shopby_orders(
    config, 
    shopby_orders: List[Dict[str, Any]], 
    transformed_orders: List[Dict[str, Any]]
) -> None:
    """1시에 조회한 샵바이 주문 데이터를 1:30 업로드를 위해 저장"""
    try:
        outputs_dir = config.data_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime("%Y%m%d")
        
        # 샵바이 주문 원본 저장
        shopby_file = outputs_dir / f"shopby_orders_{today}.json"
        with open(shopby_file, 'w', encoding='utf-8') as f:
            json.dump(shopby_orders, f, indent=2, ensure_ascii=False, default=str)
        
        # 변환된 주문 데이터 저장
        transformed_file = outputs_dir / f"transformed_orders_{today}.json"
        with open(transformed_file, 'w', encoding='utf-8') as f:
            json.dump(transformed_orders, f, indent=2, ensure_ascii=False, default=str)
        
        # SKU 매핑도 저장 (1:30에 필요)
        from sku_mapping import get_sku_mapping
        sku_mapping = get_sku_mapping(config)
        sku_file = outputs_dir / f"sku_mapping_{today}.json"
        with open(sku_file, 'w', encoding='utf-8') as f:
            json.dump(sku_mapping, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 샵바이 주문 저장: {shopby_file}")
        print(f"✅ 변환된 주문 저장: {transformed_file}")
        print(f"✅ SKU 매핑 저장: {sku_file}")
        
    except Exception as e:
        print(f"❌ 샵바이 주문 저장 실패: {e}")


async def load_shopby_orders(config) -> tuple:
    """1:30에 1시에 저장된 샵바이 주문 데이터를 로드"""
    try:
        outputs_dir = config.data_dir / "outputs"
        today = datetime.now().strftime("%Y%m%d")
        
        # 샵바이 주문 로드
        shopby_file = outputs_dir / f"shopby_orders_{today}.json"
        if not shopby_file.exists():
            print(f"❌ 샵바이 주문 파일 없음: {shopby_file}")
            return [], {}
        
        with open(shopby_file, 'r', encoding='utf-8') as f:
            shopby_orders = json.load(f)
        
        # SKU 매핑 로드
        sku_file = outputs_dir / f"sku_mapping_{today}.json"
        sku_mapping = {}
        if sku_file.exists():
            with open(sku_file, 'r', encoding='utf-8') as f:
                sku_mapping = json.load(f)
        else:
            # 파일이 없으면 다시 로드
            from sku_mapping import get_sku_mapping
            sku_mapping = get_sku_mapping(config)
        
        print(f"✅ 샵바이 주문 로드: {len(shopby_orders)}개")
        print(f"✅ SKU 매핑 로드: {len(sku_mapping)}개")
        
        return shopby_orders, sku_mapping
        
    except Exception as e:
        print(f"❌ 샵바이 주문 로드 실패: {e}")
        return [], {}


async def save_cornerlogis_result(config, result: Dict[str, Any]) -> None:
    """코너로지스 업로드 결과 저장"""
    try:
        outputs_dir = config.data_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 코너로지스 결과 저장
        result_file = outputs_dir / f"cornerlogis_result_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 코너로지스 결과 저장: {result_file}")
        
    except Exception as e:
        print(f"❌ 코너로지스 결과 저장 실패: {e}")


async def save_processing_result(
    config,
    result: Dict[str, Any],
    transformed_orders: List[Dict[str, Any]]
) -> None:
    """처리 결과를 파일로 저장"""
    try:
        outputs_dir = config.data_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 처리 결과 저장
        result_file = outputs_dir / f"processing_result_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        # 변환된 주문 데이터 저장
        orders_file = outputs_dir / f"transformed_orders_{timestamp}.json"
        with open(orders_file, 'w', encoding='utf-8') as f:
            json.dump(transformed_orders, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"처리 결과 저장: {result_file}")
        print(f"변환된 주문 저장: {orders_file}")
        
    except Exception as e:
        print(f"결과 저장 실패: {e}")


def should_run_shopby_now_kst() -> bool:
    """
    샵바이 주문 조회 실행 조건 확인
    (평일 13:00, 한국 공휴일 제외)
    """
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    # 평일 확인 (월요일=0, 일요일=6)
    if now.weekday() >= 5:  # 토요일, 일요일
        return False
    
    # 한국 공휴일 확인
    kr_holidays = holidays.SouthKorea()
    if now.date() in kr_holidays:
        return False
    
    # 13시 확인 (13:00-13:59)
    if now.hour != 13:
        return False
    
    return True


def should_run_cornerlogis_now_kst() -> bool:
    """
    코너로지스 업로드 실행 조건 확인
    (평일 13:30, 한국 공휴일 제외)
    """
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    
    # 평일 확인 (월요일=0, 일요일=6)
    if now.weekday() >= 5:  # 토요일, 일요일
        return False
    
    # 한국 공휴일 확인
    kr_holidays = holidays.SouthKorea()
    if now.date() in kr_holidays:
        return False
    
    # 13:30 확인 (13:30-13:59)
    if now.hour != 13 or now.minute < 30:
        return False
    
    return True


async def scheduled_shopby_run():
    """샵바이 주문 조회 스케줄 실행 (평일 13:00)"""
    print(f"샵바이 스케줄 체크: {datetime.now()}")
    
    if should_run_shopby_now_kst():
        print("📋 실행 조건 만족 - 샵바이 주문 조회 시작")
        result = await process_shopby_orders()
        return result
    else:
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        print(f"⏰ 실행 조건 불만족 - {now} (평일 13시만 실행)")
        return {"status": "skipped", "reason": "shopby_schedule_condition_not_met", "time": now.isoformat()}


async def scheduled_cornerlogis_run():
    """코너로지스 업로드 스케줄 실행 (평일 13:30)"""
    print(f"코너로지스 스케줄 체크: {datetime.now()}")
    
    if should_run_cornerlogis_now_kst():
        print("🚀 실행 조건 만족 - 코너로지스 업로드 시작")
        result = await process_cornerlogis_upload()
        return result
    else:
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        print(f"⏰ 실행 조건 불만족 - {now} (평일 13:30만 실행)")
        return {"status": "skipped", "reason": "cornerlogis_schedule_condition_not_met", "time": now.isoformat()}


async def run_shopby_once():
    """샵바이 주문 조회만 실행 (테스트/수동용)"""
    print("📋 수동 실행: 샵바이 주문 조회")
    return await process_shopby_orders()


async def run_cornerlogis_once():
    """코너로지스 업로드만 실행 (테스트/수동용)"""
    print("🚀 수동 실행: 코너로지스 업로드")
    return await process_cornerlogis_upload()


async def run_full_once():
    """전체 플로우 연속 실행 (테스트용)"""
    print("🔄 수동 실행: 전체 플로우")
    
    # 1. 샵바이 주문 조회
    shopby_result = await process_shopby_orders()
    
    # 2. 30초 대기 (실제로는 30분이지만 테스트용)
    print("⏳ 30초 대기 중... (실제로는 30분)")
    await asyncio.sleep(30)
    
    # 3. 코너로지스 업로드
    cornerlogis_result = await process_cornerlogis_upload()
    
    return {
        "shopby_result": shopby_result,
        "cornerlogis_result": cornerlogis_result,
        "status": "full_flow_completed"
    }


# CLI 인터페이스
async def main():
    """메인 함수"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "schedule-shopby":
            # 샵바이 스케줄 모드 (cron 13:00)
            result = await scheduled_shopby_run()
        elif command == "schedule-cornerlogis":
            # 코너로지스 스케줄 모드 (cron 13:30)
            result = await scheduled_cornerlogis_run()
        elif command == "run-shopby":
            # 샵바이만 즉시 실행
            result = await run_shopby_once()
        elif command == "run-cornerlogis":
            # 코너로지스만 즉시 실행
            result = await run_cornerlogis_once()
        elif command == "run-full":
            # 전체 플로우 연속 실행
            result = await run_full_once()
        elif command == "test":
            # 테스트 모드 (API 호출 없이 검증만)
            result = await test_workflow()
        else:
            print(f"알 수 없는 명령: {command}")
            print("사용법:")
            print("  python -m Ship_API.main schedule-shopby     # 샵바이 스케줄 (13:00)")
            print("  python -m Ship_API.main schedule-cornerlogis # 코너로지스 스케줄 (13:30)")
            print("  python -m Ship_API.main run-shopby          # 샵바이 즉시 실행")
            print("  python -m Ship_API.main run-cornerlogis     # 코너로지스 즉시 실행")
            print("  python -m Ship_API.main run-full            # 전체 플로우 연속 실행")
            print("  python -m Ship_API.main test                # 워크플로우 테스트")
            return
    else:
        # 기본값: 샵바이 스케줄 모드
        result = await scheduled_shopby_run()
    
    print(f"\n최종 결과: {result['status']}")
    return result


async def test_workflow():
    """워크플로우 테스트 (실제 API 호출 없이)"""
    print("=== 워크플로우 테스트 ===")
    
    config = load_app_config()
    
    # 설정 확인
    print(f"설정 확인:")
    print(f"  데이터 디렉토리: {config.data_dir}")
    print(f"  샵바이 API URL: {config.shopby.base_url}")
    print(f"  코너로지스 API URL: {config.cornerlogis.base_url}")
    
    # SKU 매핑 테스트
    sku_mapping = get_sku_mapping(config)
    print(f"  SKU 매핑: {len(sku_mapping)}개 항목")
    
    # 데이터 변환 테스트
    from data_transformer import create_sample_data
    transformer = ShopbyToCornerlogisTransformer(sku_mapping)
    sample_order = create_sample_data()
    transformed = transformer.transform_order(sample_order)
    
    print(f"  데이터 변환 테스트: {'성공' if transformed else '실패'}")
    
    # 유효성 검사
    errors = transformer.validate_transformed_data(transformed)
    print(f"  유효성 검사: {'통과' if not errors else f'실패 ({len(errors)}개 오류)'}")
    
    return {
        "status": "test_completed",
        "config_ok": True,
        "sku_mapping_count": len(sku_mapping),
        "data_transformation_ok": bool(transformed),
        "validation_errors": errors
    }


async def run_full_workflow():
    """전체 워크플로우 실행 (샵바이 조회 + 코너로지스 업로드)"""
    print("=" * 80)
    print("🚀 전체 워크플로우 실행")
    print("=" * 80)
    
    try:
        # 1단계: 샵바이 주문 조회
        shopby_result = await process_shopby_orders()
        
        # 2단계: 코너로지스 업로드
        cornerlogis_result = await process_cornerlogis_upload()
        
        return {
            "status": "completed",
            "shopby_result": shopby_result,
            "cornerlogis_result": cornerlogis_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ 전체 워크플로우 실행 실패: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def test_connections():
    """API 연결 테스트"""
    print("=" * 80)
    print("🧪 API 연결 테스트")
    print("=" * 80)
    
    config = load_app_config()
    results = {
        "shopby_api": False,
        "cornerlogis_api": False,
        "google_sheets": False,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # 샵바이 API 테스트
        async with ShopbyApiClient(config.shopby) as shopby_client:
            try:
                await shopby_client.get_orders_by_date_range(days_back=1)
                results["shopby_api"] = True
                print("✅ 샵바이 API 연결 성공")
            except Exception as e:
                print(f"❌ 샵바이 API 연결 실패: {e}")
        
        # 코너로지스 API 테스트
        async with CornerlogisApiClient(config.cornerlogis) as cornerlogis_client:
            try:
                # 간단한 상품 조회 테스트
                await cornerlogis_client.get_goods_ids(["TEST"])
                results["cornerlogis_api"] = True
                print("✅ 코너로지스 API 연결 성공")
            except Exception as e:
                print(f"❌ 코너로지스 API 연결 실패: {e}")
        
        # 구글 시트 테스트
        try:
            sku_mapping = get_sku_mapping(config)
            results["google_sheets"] = True
            print(f"✅ 구글 시트 연결 성공: {len(sku_mapping)}개 매핑")
        except Exception as e:
            print(f"❌ 구글 시트 연결 실패: {e}")
        
        return results
        
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")
        results["error"] = str(e)
        return results


if __name__ == "__main__":
    asyncio.run(main())
