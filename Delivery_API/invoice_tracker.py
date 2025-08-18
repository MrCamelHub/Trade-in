"""
송장번호 추적 및 자동 상태 업데이트 로직
코너로지스 → 샵바이 송장번호 동기화
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from cornerlogis_production_client import CornerlogisProductionClient
from shopby_delivery_client import ShopbyDeliveryClient


class InvoiceTracker:
    """송장번호 추적 및 상태 동기화 관리자"""
    
    def __init__(self):
        self.cornerlogis_client = CornerlogisProductionClient()
        self.shopby_client = ShopbyDeliveryClient()
    
    async def __aenter__(self):
        await self.cornerlogis_client.__aenter__()
        await self.shopby_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cornerlogis_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.shopby_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_orders_needing_update(self) -> List[Dict[str, Any]]:
        """
        송장번호 업데이트가 필요한 주문들 조회
        
        Returns:
            업데이트가 필요한 주문 목록
        """
        print("🔍 송장번호 업데이트가 필요한 주문 조회 시작...")
        print("=" * 60)
        
        # 1. 코너로지스에서 송장번호가 있는 주문들 조회
        print("📡 1단계: 코너로지스에서 송장번호가 있는 주문들 조회")
        cornerlogis_orders = await self.cornerlogis_client.get_orders_with_new_invoices()
        print(f"   ✅ 코너로지스에서 {len(cornerlogis_orders)}건의 배송완료 주문 발견")
        
        update_candidates = []
        skip_count = 0
        no_delivery_no_count = 0
        
        for i, order in enumerate(cornerlogis_orders, 1):
            print(f"\n📦 [{i}/{len(cornerlogis_orders)}] 주문 분석 중...")
            
            # 2. 샵바이 주문번호 추출
            shopby_order_no = self.cornerlogis_client.extract_shopby_order_no(
                order.get("companyOrderId", "")
            )
            print(f"   🔍 코너로지스 주문ID: {order.get('companyOrderId', 'N/A')}")
            print(f"   🔍 추출된 샵바이 주문번호: {shopby_order_no}")
            print(f"   📋 송장번호: {order.get('invoiceNo', 'N/A')}")
            
            # 3. 샵바이에서 주문 상세 조회 (originalDeliveryNo 확인)
            print(f"   📞 샵바이 주문 상세 조회 중...")
            shopby_details = await self.shopby_client.get_order_details(shopby_order_no)
            
            if shopby_details:
                original_delivery_no = shopby_details.get("originalDeliveryNo")
                print(f"   ✅ 샵바이 주문 조회 성공")
                print(f"   🚚 샵바이 배송번호(originalDeliveryNo): {original_delivery_no}")
                
                # 4. 송장번호 상태 확인
                delivery_groups = shopby_details.get("deliveryGroups", [])
                current_invoice = None
                if delivery_groups:
                    current_invoice = delivery_groups[0].get("invoiceNo", "")
                    
                print(f"   📋 샵바이 현재 송장번호: {current_invoice if current_invoice else '없음'}")
                print(f"   📋 코너로지스 송장번호: {order.get('invoiceNo', 'N/A')}")
                
                # 5. 업데이트 필요성 판단
                if original_delivery_no:
                    if current_invoice and current_invoice == order.get('invoiceNo'):
                        print(f"   ✨ 이미 업데이트 완료: 송장번호가 일치함 ({current_invoice})")
                        skip_count += 1
                    elif current_invoice and current_invoice != order.get('invoiceNo'):
                        print(f"   ⚠️ 송장번호 불일치: 샵바이({current_invoice}) vs 코너로지스({order.get('invoiceNo')})")
                        print(f"   🔄 업데이트 필요: 코너로지스 송장번호로 갱신 예정")
                        update_info = {
                            "shopby_order_no": shopby_order_no,
                            "original_delivery_no": original_delivery_no,
                            "invoice_no": order.get("invoiceNo"),
                            "cornerlogis_order": order,
                            "shopby_order": shopby_details,
                            "pickup_complete_at": order.get("pickupCompleteAt"),
                            "arrival_at": order.get("arrivalAt"),
                            "status": order.get("status")
                        }
                        update_candidates.append(update_info)
                        print(f"   ✅ 업데이트 대상으로 추가됨")
                    else:
                        print(f"   🆕 신규 송장번호 등록: 샵바이에 송장번호 없음")
                        print(f"   🔄 업데이트 필요: 코너로지스 송장번호 등록 예정")
                        update_info = {
                            "shopby_order_no": shopby_order_no,
                            "original_delivery_no": original_delivery_no,
                            "invoice_no": order.get("invoiceNo"),
                            "cornerlogis_order": order,
                            "shopby_order": shopby_details,
                            "pickup_complete_at": order.get("pickupCompleteAt"),
                            "arrival_at": order.get("arrivalAt"),
                            "status": order.get("status")
                        }
                        update_candidates.append(update_info)
                        print(f"   ✅ 업데이트 대상으로 추가됨")
                else:
                    print(f"   ❌ 배송번호(originalDeliveryNo) 없음: 샵바이에서 배송 처리가 안된 상태")
                    print(f"   ⏸️ 스킵: 배송 처리 후 재시도 필요")
                    no_delivery_no_count += 1
            else:
                print(f"   ❌ 샵바이 주문 조회 실패: {shopby_order_no}")
                print(f"   ⏸️ 스킵: API 오류 또는 주문번호 불일치")
            
            # API 호출 간격 조절
            await asyncio.sleep(0.5)
        
        print(f"\n" + "=" * 60)
        print(f"📊 최종 분석 결과 요약:")
        print(f"   🔍 분석한 총 주문 수: {len(cornerlogis_orders)}건")
        print(f"   ✅ 업데이트 대상: {len(update_candidates)}건")
        print(f"   ✨ 이미 완료된 주문: {skip_count}건 (송장번호 일치)")
        print(f"   ❌ 배송번호 없는 주문: {no_delivery_no_count}건 (샵바이 배송 처리 대기)")
        print(f"   ⏸️ 기타 스킵: {len(cornerlogis_orders) - len(update_candidates) - skip_count - no_delivery_no_count}건")
        print("=" * 60)
        
        return update_candidates
    
    async def update_order_status(
        self, 
        update_info: Dict[str, Any],
        delivery_company_type: str = "POST",
        order_status_type: str = "DELIVERY_ING"
    ) -> bool:
        """
        단일 주문의 상태 업데이트
        
        Args:
            update_info: 업데이트 정보
            delivery_company_type: 택배사 타입
            order_status_type: 변경할 주문 상태
            
        Returns:
            성공 여부
        """
        shipping_no = update_info["original_delivery_no"]
        invoice_no = update_info["invoice_no"]
        order_no = update_info["shopby_order_no"]
        
        print(f"🚚 주문 상태 업데이트 실행:")
        print(f"   주문번호: {order_no}")
        print(f"   배송번호: {shipping_no}")
        print(f"   송장번호: {invoice_no}")
        print(f"   택배사: {delivery_company_type}")
        print(f"   상태: {order_status_type}")
        
        success = await self.shopby_client.change_order_status_by_shipping_no(
            shipping_no=shipping_no,
            invoice_no=invoice_no,
            delivery_company_type=delivery_company_type,
            order_status_type=order_status_type
        )
        
        if success:
            print(f"✅ 주문 상태 업데이트 성공: {order_no}")
        else:
            print(f"❌ 주문 상태 업데이트 실패: {order_no}")
        
        return success
    
    async def batch_update_orders(
        self,
        update_list: List[Dict[str, Any]],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        주문 상태 일괄 업데이트
        
        Args:
            update_list: 업데이트할 주문 목록
            dry_run: 실제 업데이트 없이 시뮬레이션만 실행
            
        Returns:
            업데이트 결과 요약
        """
        print(f"\n🔄 일괄 주문 상태 업데이트 실행")
        print("=" * 60)
        print(f"   🎯 모드: {'시뮬레이션 (DRY RUN)' if dry_run else '실제 업데이트'}")
        print(f"   📋 대상 주문 수: {len(update_list)}건")
        print("=" * 60)
        
        success_count = 0
        failure_count = 0
        results = []
        
        for i, update_info in enumerate(update_list, 1):
            order_no = update_info["shopby_order_no"]
            invoice_no = update_info["invoice_no"]
            original_delivery_no = update_info["original_delivery_no"]
            
            print(f"   📦 주문번호: {order_no}")
            print(f"   🚚 배송번호: {original_delivery_no}")
            print(f"   📋 송장번호: {invoice_no}")
            
            if dry_run:
                print(f"   🔍 DRY RUN: 시뮬레이션 모드 - 실제 업데이트하지 않음")
                success = True  # 시뮬레이션에서는 성공으로 처리
            else:
                print(f"   🚀 실제 업데이트 실행 중...")
                success = await self.update_order_status(update_info)
                # API 호출 간격 조절
                await asyncio.sleep(1.0)
            
            result = {
                "order_no": order_no,
                "invoice_no": invoice_no,
                "original_delivery_no": update_info["original_delivery_no"],
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
            
            if success:
                success_count += 1
                print(f"   ✅ 처리 완료: 성공")
            else:
                failure_count += 1
                print(f"   ❌ 처리 실패: 오류 발생")
        
        summary = {
            "total_processed": len(update_list),
            "success_count": success_count,
            "failure_count": failure_count,
            "dry_run": dry_run,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n" + "=" * 60)
        print(f"📊 일괄 업데이트 최종 결과:")
        print(f"   📋 처리 총 건수: {summary['total_processed']}건")
        print(f"   ✅ 성공: {summary['success_count']}건")
        print(f"   ❌ 실패: {summary['failure_count']}건")
        print(f"   🔍 모드: {'시뮬레이션 (DRY RUN)' if summary['dry_run'] else '실제 업데이트'}")
        print("=" * 60)
        
        return summary
    
    async def run_full_sync(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        전체 송장번호 동기화 실행
        
        Args:
            dry_run: 실제 업데이트 없이 시뮬레이션만 실행
            
        Returns:
            동기화 결과
        """
        print("🚀 전체 송장번호 동기화 시작...")
        start_time = datetime.now()
        
        try:
            # 1. 업데이트가 필요한 주문들 조회
            update_candidates = await self.get_orders_needing_update()
            
            if not update_candidates:
                print("📝 업데이트가 필요한 주문이 없습니다.")
                return {
                    "status": "completed",
                    "message": "업데이트가 필요한 주문이 없음",
                    "total_candidates": 0,
                    "dry_run": dry_run,
                    "timestamp": datetime.now().isoformat()
                }
            
            # 2. 일괄 업데이트 실행
            update_result = await self.batch_update_orders(update_candidates, dry_run=dry_run)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "status": "completed",
                "duration_seconds": duration,
                "candidates_found": len(update_candidates),
                "update_result": update_result,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            print(f"🎉 전체 동기화 완료 (소요시간: {duration:.2f}초)")
            return result
            
        except Exception as e:
            print(f"❌ 동기화 중 오류 발생: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 테스트 함수
async def test_invoice_tracker():
    """송장번호 추적기 테스트"""
    async with InvoiceTracker() as tracker:
        print("🚀 송장번호 추적기 테스트 시작...")
        
        # DRY RUN으로 전체 동기화 테스트
        result = await tracker.run_full_sync(dry_run=True)
        
        print(f"\n📊 테스트 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_invoice_tracker())
