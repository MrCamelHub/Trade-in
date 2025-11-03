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
        
        # 제외할 주문 정보 설정
        self.excluded_orders = {
            "202508310722335114": {  # 주문번호
                "shipping_no": "75802477",  # 배송번호
                "sku": "50004234",  # SKU
                "reason": "사용자 요청으로 배송 처리 제외"
            }
        }
    
    async def __aenter__(self):
        await self.cornerlogis_client.__aenter__()
        await self.shopby_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cornerlogis_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.shopby_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def is_order_excluded(self, order_info: Dict[str, Any]) -> Tuple[bool, str]:
        """
        주문이 제외 대상인지 확인
        
        Args:
            order_info: 주문 정보
            
        Returns:
            (제외 여부, 제외 사유)
        """
        # 샵바이 주문번호 추출
        company_order_id = order_info.get("companyOrderId", "")
        shopby_order_no = self.cornerlogis_client.extract_shopby_order_no(company_order_id)
        
        # 제외 대상 주문인지 확인
        if shopby_order_no in self.excluded_orders:
            excluded_info = self.excluded_orders[shopby_order_no]
            reason = excluded_info["reason"]
            
            print(f"   🚫 제외 대상 주문 발견:")
            print(f"     주문번호: {shopby_order_no}")
            print(f"     배송번호: {excluded_info['shipping_no']}")
            print(f"     SKU: {excluded_info['sku']}")
            print(f"     제외 사유: {reason}")
            
            return True, reason
        
        return False, ""
    
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
            
            # 1.5. 제외 대상 주문인지 확인
            is_excluded, exclusion_reason = self.is_order_excluded(order)
            if is_excluded:
                print(f"   ⏸️ 제외 대상 주문: {exclusion_reason}")
                skip_count += 1
                continue
            
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
                
                # 4. 샵바이 주문 상태 및 송장번호 확인
                delivery_groups = shopby_details.get("deliveryGroups", [])
                current_invoice = None
                order_status = "알 수 없음"
                
                if delivery_groups:
                    current_invoice = delivery_groups[0].get("invoiceNo", "")
                    # deliveryGroups[0].orderProducts[0].orderProductOptions[0].orderStatusType에서 상태 확인
                    order_products = delivery_groups[0].get("orderProducts", [])
                    if order_products:
                        options = order_products[0].get("orderProductOptions", [])
                        if options:
                            order_status = options[0].get("orderStatusType", "알 수 없음")
                    
                print(f"   📋 샵바이 현재 송장번호: {current_invoice if current_invoice else '없음'}")
                print(f"   📋 코너로지스 송장번호: {order.get('invoiceNo', 'N/A')}")
                print(f"   📊 샵바이 주문 상태: {order_status}")
                
                # 5. 업데이트 가능 상태 확인
                updatable_statuses = ["PAY_DONE", "DELIVERY_PREPARE"]
                is_updatable_status = order_status in updatable_statuses
                
                print(f"   🎯 업데이트 가능 상태: {is_updatable_status} ({order_status})")
                
                # 6. 업데이트 필요성 판단
                if original_delivery_no and is_updatable_status:
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
                elif original_delivery_no and not is_updatable_status:
                    print(f"   ⏸️ 업데이트 불가 상태: {order_status} (PAY_DONE/DELIVERY_PREPARE 아님)")
                    print(f"   ⏸️ 스킵: 이미 배송 중이거나 완료된 주문")
                    skip_count += 1
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
        print(f"   ✅ 업데이트 대상: {len(update_candidates)}건 (PAY_DONE/DELIVERY_PREPARE 상태)")
        print(f"   ✨ 이미 완료된 주문: {skip_count}건 (송장번호 일치 또는 업데이트 불가 상태)")
        print(f"   ❌ 배송번호 없는 주문: {no_delivery_no_count}건 (샵바이 배송 처리 대기)")
        print(f"   ⏸️ 기타 스킵: {len(cornerlogis_orders) - len(update_candidates) - skip_count - no_delivery_no_count}건")
        print("=" * 60)
        
        return update_candidates
    
    async def update_order_status(
        self,
        update_info: Dict[str, Any],
        delivery_company_type: str = "LOTTE",
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
    
    async def get_orders_needing_delivery_completion(self) -> List[Dict[str, Any]]:
        """
        배송완료 처리가 필요한 주문들 조회
        (arrivalAt이 있지만 샵바이에서 아직 DELIVERY_DONE이 아닌 주문들)
        
        Returns:
            배송완료 처리가 필요한 주문 목록
        """
        print("🔍 배송완료 처리가 필요한 주문 조회 시작...")
        print("=" * 60)
        
        # 1. 코너로지스에서 배송완료된 주문들 조회
        print("📡 1단계: 코너로지스에서 배송완료된 주문들 조회")
        cornerlogis_orders = await self.cornerlogis_client.get_orders_with_new_invoices()
        
        # arrivalAt이 있는 주문들만 필터링
        arrived_orders = []
        for order in cornerlogis_orders:
            arrival_at = order.get("arrivalAt")
            if arrival_at and arrival_at.strip():  # null이 아니고 빈 문자열도 아닌 경우
                arrived_orders.append(order)
        
        print(f"   ✅ 배송완료된 주문: {len(arrived_orders)}건")
        
        completion_candidates = []
        skip_count = 0
        no_delivery_no_count = 0
        
        for i, order in enumerate(arrived_orders, 1):
            print(f"\n📦 [{i}/{len(arrived_orders)}] 배송완료 주문 분석 중...")
            
            # 1.5. 제외 대상 주문인지 확인
            is_excluded, exclusion_reason = self.is_order_excluded(order)
            if is_excluded:
                print(f"   ⏸️ 제외 대상 주문: {exclusion_reason}")
                skip_count += 1
                continue
            
            # 2. 샵바이 주문번호 추출
            shopby_order_no = self.cornerlogis_client.extract_shopby_order_no(
                order.get("companyOrderId", "")
            )
            print(f"   🔍 코너로지스 주문ID: {order.get('companyOrderId', 'N/A')}")
            print(f"   🔍 추출된 샵바이 주문번호: {shopby_order_no}")
            print(f"   📅 배송완료 시간: {order.get('arrivalAt', 'N/A')}")
            
            # 3. 샵바이에서 주문 상세 조회
            print(f"   📞 샵바이 주문 상세 조회 중...")
            shopby_details = await self.shopby_client.get_order_details(shopby_order_no)
            
            if shopby_details:
                original_delivery_no = shopby_details.get("originalDeliveryNo")
                print(f"   ✅ 샵바이 주문 조회 성공")
                print(f"   🚚 샵바이 배송번호(originalDeliveryNo): {original_delivery_no}")
                
                # 4. 샵바이 주문 상태 확인
                delivery_groups = shopby_details.get("deliveryGroups", [])
                order_status = "알 수 없음"
                
                if delivery_groups:
                    order_products = delivery_groups[0].get("orderProducts", [])
                    if order_products:
                        options = order_products[0].get("orderProductOptions", [])
                        if options:
                            order_status = options[0].get("orderStatusType", "알 수 없음")
                
                print(f"   📊 샵바이 주문 상태: {order_status}")
                
                # 5. 제한된 결제방법 확인 (상태 변경 불가)
                pay_type = shopby_details.get("payType", "")
                is_naver_pay = "NAVER" in str(pay_type).upper()
                is_escrow = "ESCROW" in str(pay_type).upper()
                is_restricted_payment = is_naver_pay or is_escrow
                
                print(f"   💳 결제방법: {pay_type}")
                print(f"   🔍 네이버페이 주문: {is_naver_pay}")
                print(f"   🔍 에스크로 주문: {is_escrow}")
                print(f"   🚫 배송완료 처리 제한: {is_restricted_payment}")
                
                # 6. 배송완료 처리 필요성 판단
                if original_delivery_no and order_status == "DELIVERY_ING" and not is_restricted_payment:
                    print(f"   🎯 배송완료 처리 필요: 현재 배송중 → 배송완료로 변경 예정")
                    completion_info = {
                        "shopby_order_no": shopby_order_no,
                        "original_delivery_no": original_delivery_no,
                        "invoice_no": order.get("invoiceNo"),
                        "arrival_at": order.get("arrivalAt"),
                        "cornerlogis_order": order,
                        "shopby_order": shopby_details,
                        "status": order.get("status")
                    }
                    completion_candidates.append(completion_info)
                    print(f"   ✅ 배송완료 처리 대상으로 추가됨")
                elif original_delivery_no and order_status == "DELIVERY_DONE":
                    print(f"   ✨ 이미 배송완료 처리됨: {order_status}")
                    skip_count += 1
                elif original_delivery_no and order_status == "DELIVERY_ING" and is_restricted_payment:
                    if is_naver_pay:
                        print(f"   ⏸️ 네이버페이 주문: 샵바이 정책상 배송완료 처리 불가")
                    elif is_escrow:
                        print(f"   ⏸️ 에스크로 주문: 샵바이 정책상 배송완료 처리 불가")
                    else:
                        print(f"   ⏸️ 제한된 결제방법: 샵바이 정책상 배송완료 처리 불가")
                    skip_count += 1
                elif original_delivery_no and order_status not in ["DELIVERY_ING", "DELIVERY_DONE"]:
                    print(f"   ⏸️ 배송완료 처리 불가: {order_status} (DELIVERY_ING 상태 아님)")
                    skip_count += 1
                else:
                    print(f"   ❌ 배송번호(originalDeliveryNo) 없음")
                    no_delivery_no_count += 1
            else:
                print(f"   ❌ 샵바이 주문 조회 실패: {shopby_order_no}")
            
            # API 호출 간격 조절
            await asyncio.sleep(0.5)
        
        print(f"\n" + "=" * 60)
        print(f"📊 배송완료 처리 분석 결과:")
        print(f"   🔍 분석한 배송완료 주문 수: {len(arrived_orders)}건")
        print(f"   ✅ 배송완료 처리 대상: {len(completion_candidates)}건 (DELIVERY_ING → DELIVERY_DONE)")
        print(f"   ✨ 이미 완료된 주문: {skip_count}건")
        print(f"   ❌ 배송번호 없는 주문: {no_delivery_no_count}건")
        print("=" * 60)
        
        return completion_candidates
    
    async def batch_complete_deliveries(
        self,
        completion_list: List[Dict[str, Any]],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        주문 배송완료 처리 일괄 실행
        
        Args:
            completion_list: 배송완료 처리할 주문 목록
            dry_run: 실제 업데이트 없이 시뮬레이션만 실행
            
        Returns:
            배송완료 처리 결과 요약
        """
        print(f"\n🔄 일괄 배송완료 처리 실행")
        print("=" * 60)
        print(f"   🎯 모드: {'시뮬레이션 (DRY RUN)' if dry_run else '실제 처리'}")
        print(f"   📋 대상 주문 수: {len(completion_list)}건")
        print("=" * 60)
        
        success_count = 0
        failure_count = 0
        results = []
        
        for i, completion_info in enumerate(completion_list, 1):
            order_no = completion_info["shopby_order_no"]
            original_delivery_no = completion_info["original_delivery_no"]
            invoice_no = completion_info["invoice_no"]
            arrival_at = completion_info["arrival_at"]
            
            print(f"   📦 주문번호: {order_no}")
            print(f"   🚚 배송번호: {original_delivery_no}")
            print(f"   📋 송장번호: {invoice_no}")
            print(f"   📅 배송완료: {arrival_at}")
            
            if dry_run:
                print(f"   🔍 DRY RUN: 시뮬레이션 모드 - 실제 처리하지 않음")
                success = True
            else:
                print(f"   🚀 실제 배송완료 처리 실행 중...")
                # DELIVERY_DONE 상태로 변경
                success = await self.shopby_client.change_order_status_by_shipping_no(
                    shipping_no=original_delivery_no,
                    invoice_no=invoice_no,
                    delivery_company_type="LOTTE",
                    order_status_type="DELIVERY_DONE"
                )
                # API 호출 간격 조절
                await asyncio.sleep(1.0)
            
            result = {
                "order_no": order_no,
                "original_delivery_no": original_delivery_no,
                "invoice_no": invoice_no,
                "arrival_at": arrival_at,
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
            "total_processed": len(completion_list),
            "success_count": success_count,
            "failure_count": failure_count,
            "dry_run": dry_run,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n" + "=" * 60)
        print(f"📊 배송완료 처리 최종 결과:")
        print(f"   📋 처리 총 건수: {summary['total_processed']}건")
        print(f"   ✅ 성공: {summary['success_count']}건")
        print(f"   ❌ 실패: {summary['failure_count']}건")
        print(f"   🔍 모드: {'시뮬레이션 (DRY RUN)' if summary['dry_run'] else '실제 처리'}")
        print("=" * 60)
        
        return summary
    
    async def run_full_sync(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        전체 주문 동기화 실행 (송장번호 업데이트 + 배송완료 처리)
        
        Args:
            dry_run: 실제 업데이트 없이 시뮬레이션만 실행
            
        Returns:
            동기화 결과
        """
        print("🚀 전체 주문 동기화 시작 (송장번호 업데이트 + 배송완료 처리)")
        print("=" * 80)
        start_time = datetime.now()
        
        try:
            # 1. 송장번호 업데이트가 필요한 주문들 조회 및 처리
            print("📋 1단계: 송장번호 업데이트 처리")
            update_candidates = await self.get_orders_needing_update()
            
            update_result = None
            if update_candidates:
                # 송장번호 업데이트 실행
                update_result = await self.batch_update_orders(update_candidates, dry_run=dry_run)
            else:
                print("📝 송장번호 업데이트가 필요한 주문이 없습니다.")
                update_result = {
                    "total_processed": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "dry_run": dry_run,
                    "results": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 2. 배송완료 처리가 필요한 주문들 조회 및 처리
            print(f"\n📋 2단계: 배송완료 처리")
            completion_candidates = await self.get_orders_needing_delivery_completion()
            
            completion_result = None
            if completion_candidates:
                # 배송완료 처리 실행
                completion_result = await self.batch_complete_deliveries(completion_candidates, dry_run=dry_run)
            else:
                print("📝 배송완료 처리가 필요한 주문이 없습니다.")
                completion_result = {
                    "total_processed": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "dry_run": dry_run,
                    "results": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 3. 최종 결과 요약
            print(f"\n" + "=" * 80)
            print(f"🎉 전체 주문 동기화 최종 결과:")
            print(f"   ⏱️ 소요 시간: {duration:.2f}초")
            print(f"   📋 송장번호 업데이트: {update_result['success_count']}/{update_result['total_processed']}건 성공")
            print(f"   📦 배송완료 처리: {completion_result['success_count']}/{completion_result['total_processed']}건 성공")
            print(f"   🔍 모드: {'시뮬레이션 (DRY RUN)' if dry_run else '실제 처리'}")
            print("=" * 80)
            
            result = {
                "status": "completed",
                "duration_seconds": duration,
                "invoice_update": {
                "candidates_found": len(update_candidates),
                    "result": update_result
                },
                "delivery_completion": {
                    "candidates_found": len(completion_candidates),
                    "result": completion_result
                },
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "dry_run": dry_run
            }
            
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
