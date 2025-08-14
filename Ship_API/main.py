from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import pytz
import holidays

from .config import load_app_config, ensure_data_dirs
from .shopby_api_client import ShopbyApiClient
from .cornerlogis_api_client import CornerlogisApiClient
from .data_transformer import ShopbyToCornerlogisTransformer
from .sku_mapping import get_sku_mapping
from .google_sheets_logger import GoogleSheetsLogger


async def process_orders() -> Dict[str, Any]:
    """
    전체 주문 처리 워크플로우
    
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
        
        # 1. SKU 매핑 로드
        print("1. SKU 매핑 로드 중...")
        sku_mapping = get_sku_mapping(config)
        print(f"SKU 매핑 로드 완료: {len(sku_mapping)}개 항목")
        
        # 2. 샵바이에서 주문 조회
        print("2. 샵바이 API에서 주문 조회 중...")
        shopby_orders = []
        
        async with ShopbyApiClient(config.shopby) as shopby_client:
            # 오늘 주문 조회
            shopby_orders = await shopby_client.get_today_orders()
            result["shopby_orders_count"] = len(shopby_orders)
            print(f"샵바이 주문 조회 완료: {len(shopby_orders)}개 주문")

        # 2.5. 구글시트 로깅 (상품명, 상품번호)
        try:
            logger = GoogleSheetsLogger(
                spreadsheet_id=config.logging.spreadsheet_id,
                tab_name=config.logging.tab_name,
                google_credentials_json=config.google_credentials_json,
                google_credentials_path=str(config.google_credentials_path) if config.google_credentials_path else None,
            )
            logged = logger.log_from_shopby_orders(shopby_orders)
            print(f"구글시트 로깅 완료: {logged}개 상품")
        except Exception as e:
            print(f"구글시트 로깅 실패: {e}")
        
        if not shopby_orders:
            print("처리할 주문이 없습니다.")
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            return result
        
        # 3. 데이터 변환
        print("3. 주문 데이터 변환 중...")
        transformer = ShopbyToCornerlogisTransformer(sku_mapping)
        transformed_orders = transformer.transform_orders(shopby_orders)
        result["transformed_orders_count"] = len(transformed_orders)
        print(f"데이터 변환 완료: {len(transformed_orders)}개 주문")
        
        if not transformed_orders:
            print("변환된 주문이 없습니다.")
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            return result
        
        # 4. 코너로지스 API로 전송
        print("4. 코너로지스 API로 주문 전송 중...")
        
        async with CornerlogisApiClient(config.cornerlogis) as cornerlogis_client:
            # 개별 주문 처리
            for i, shopby_order in enumerate(shopby_orders):
                order_no = shopby_order.get("orderNo", f"ORDER_{i+1}")
                
                try:
                    print(f"주문 처리 중: {order_no} ({i+1}/{len(shopby_orders)})")
                    
                    # 샵바이 주문 데이터를 코너로지스 출고 데이터로 변환
                    outbound_data_list = cornerlogis_client.prepare_outbound_data(shopby_order, sku_mapping)
                    
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
                    if i < len(shopby_orders) - 1:
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
        
        # 5. 결과 저장
        await save_processing_result(config, result, transformed_orders)
        
        result["status"] = "completed"
        result["end_time"] = datetime.now().isoformat()
        
        print("=== 처리 완료 ===")
        print(f"총 샵바이 주문: {result['shopby_orders_count']}")
        print(f"변환된 주문: {result['transformed_orders_count']}")
        print(f"코너로지스 전송 성공: {result['cornerlogis_success_count']}")
        print(f"코너로지스 전송 실패: {result['cornerlogis_failure_count']}")
        
        if result["errors"]:
            print(f"오류 수: {len(result['errors'])}")
            for error in result["errors"][:5]:  # 최대 5개만 출력
                print(f"  - {error}")
        
        return result
        
    except Exception as e:
        error_msg = f"전체 처리 중 치명적 오류: {str(e)}"
        print(error_msg)
        result["status"] = "failed"
        result["errors"].append(error_msg)
        result["end_time"] = datetime.now().isoformat()
        return result


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


def should_run_now_kst() -> bool:
    """
    현재 시간이 실행 조건에 맞는지 확인
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


async def scheduled_run():
    """스케줄된 실행 (매일 평일 13:00)"""
    print(f"스케줄 체크: {datetime.now()}")
    
    if should_run_now_kst():
        print("실행 조건 만족 - 주문 처리 시작")
        result = await process_orders()
        return result
    else:
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        print(f"실행 조건 불만족 - {now} (평일 13시만 실행)")
        return {"status": "skipped", "reason": "schedule_condition_not_met", "time": now.isoformat()}


async def run_once():
    """한 번만 실행 (테스트 또는 수동 실행용)"""
    print("수동 실행 모드")
    return await process_orders()


# CLI 인터페이스
async def main():
    """메인 함수"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "schedule":
            # 스케줄 모드 (cron 등에서 호출)
            result = await scheduled_run()
        elif command == "run":
            # 즉시 실행 모드
            result = await run_once()
        elif command == "test":
            # 테스트 모드 (API 호출 없이 검증만)
            result = await test_workflow()
        else:
            print(f"알 수 없는 명령: {command}")
            print("사용법: python -m Ship_API.main [schedule|run|test]")
            return
    else:
        # 기본값: 스케줄 모드
        result = await scheduled_run()
    
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
    from .data_transformer import create_sample_data
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


if __name__ == "__main__":
    asyncio.run(main())
