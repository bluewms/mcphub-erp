"""鼎捷 ERP E10 数据模型

基于接口文档定义的字段映射。
"""


# ============================================================
# 采购入库单
# ============================================================

PURCHASE_RECEIPT_HEADER_FIELDS = {
    "doc_no": {"e10": "DOC_NO", "type": "String", "length": 20, "desc": "单号"},
    "om_site_id": {"e10": "Owner_Org_PLANT_PLANT_CODE", "type": "String", "length": 6, "desc": "营运据点编号"},
    "doc_type_no": {"e10": "DOC_ID_DOC_CODE", "type": "String", "length": 4, "desc": "单据类型编号"},
    "doc_date": {"e10": "DOC_DATE", "type": "Date", "length": None, "desc": "单据日期"},
    "responsibility_employee_no": {"e10": "Owner_Emp_EMPLOYEE_CODE", "type": "String", "length": 40, "desc": "负责人员编号"},
    "department_no": {"e10": "Owner_Dept_ADMIN_UNIT_CODE", "type": "String", "length": 40, "desc": "部门编号"},
    "supplier_no": {"e10": "SUPPLIER_ID_SUPPLIER_CODE", "type": "String", "length": 40, "desc": "供应商编号"},
    "teamwork_no": {
        "e10": "GROUP_SYNERGY_ID_SUPPLY_SYNERGY_SUPPLY_SYNERGY_CODE",
        "type": "String", "length": 40, "desc": "整单协同关系编号",
    },
    "final_supplier_no": {"e10": "SOURCE_SUPPLIER_ID_SUPPLIER_CODE", "type": "String", "length": 40, "desc": "最终供应商编号"},
    "remark": {"e10": "REMARK", "type": "String", "length": 255, "desc": "备注"},
}

PURCHASE_RECEIPT_DETAIL_FIELDS = {
    "seq_no": {"e10": "SequenceNumber", "type": "Int32", "desc": "序号"},
    "source_doc_seq": {"e10": "SOURCE_ID_SequenceNumber", "type": "Int32", "desc": "来源序号"},
    "source_doc_no": {"e10": "SOURCE_ID_Parent_DOC_NO", "type": "String(20)", "desc": "来源单号"},
    "business_qty": {"e10": "BUSINESS_QTY", "type": "Decimal(16,6)", "desc": "业务数量"},
    "return_business_qty": {"e10": "RETURN_BUSINESS_QTY", "type": "Decimal(16,6)", "desc": "拒收业务数量"},
    "scrap_business_qty": {"e10": "SCRAP_BUSINESS_QTY", "type": "Decimal(16,6)", "desc": "报废业务数量"},
    "warehouse_no": {"e10": "WAREHOUSE_ID_WAREHOUSE_CODE", "type": "String(10)", "desc": "仓库编号"},
    "storage_spaces_no": {"e10": "BIN_ID_BIN_CODE", "type": "String(10)", "desc": "库位编号"},
    "lot_no": {"e10": "ITEM_LOT_ID_LOT_CODE", "type": "String(30)", "desc": "批号"},
    "remark": {"e10": "REMARK", "type": "String(255)", "desc": "备注"},
}


# ============================================================
# 销货出库单
# ============================================================

SALES_ISSUE_HEADER_FIELDS = {
    "doc_no": {"e10": "DOC_NO", "type": "String", "length": 20, "desc": "单号"},
    "doc_date": {"e10": "DOC_DATE", "type": "Date", "length": None, "desc": "单据日期"},
    "customer_no": {"e10": "SHIP_TO_CUSTOMER_ID_CUSTOMER_CODE", "type": "String", "length": 40, "desc": "客户编号"},
    "doc_type_no": {"e10": "DOC_ID_DOC_CODE", "type": "String", "length": 4, "desc": "单据类型编号"},
    "administration_unit_no": {"e10": "Owner_Dept_ADMIN_UNIT_CODE", "type": "String", "length": 40, "desc": "仓管部门编号"},
    "employee_no": {"e10": "Owner_Emp_EMPLOYEE_CODE", "type": "String", "length": 40, "desc": "仓管员编号"},
    "om_site_id": {"e10": "Owner_Org_PLANT_PLANT_CODE", "type": "String", "length": 6, "desc": "营运据点编号"},
    "remark": {"e10": "REMARK", "type": "String", "length": 255, "desc": "备注"},
}

SALES_ISSUE_DETAIL_FIELDS = {
    "seq": {"e10": "SequenceNumber", "type": "Int32", "desc": "序号"},
    "sales_delivery_seq": {
        "e10": "SOURCE_ID_SALES_DELIVERY_SALES_DELIVERY_D_SequenceNumber",
        "type": "Int32", "desc": "来源序号",
    },
    "sales_delivery_no": {
        "e10": "SOURCE_ID_SALES_DELIVERY_SALES_DELIVERY_D_Parent_DOC_NO",
        "type": "String(20)", "desc": "来源单号",
    },
    "business_qty": {"e10": "BUSINESS_QTY", "type": "Decimal(16,6)", "desc": "业务数量"},
    "warehouse_no": {"e10": "WAREHOUSE_ID_WAREHOUSE_CODE", "type": "String(10)", "desc": "仓库编号"},
    "storage_spaces_no": {"e10": "BIN_ID_BIN_CODE", "type": "String(10)", "desc": "库位编号"},
    "lot_no": {"e10": "ITEM_LOT_ID_LOT_CODE", "type": "String(30)", "desc": "批号"},
    "remark": {"e10": "REMARK", "type": "String(255)", "desc": "备注"},
    "second_qty": {"e10": "SECOND_QTY", "type": "Decimal(16,6)", "desc": "第二数量"},
}


# ============================================================
# 物料
# ============================================================

MATERIAL_FIELDS = {
    "code": {"e10": "ITEM_CODE", "type": "String", "required": True, "desc": "产品编码"},
    "name": {"e10": "ITEM_NAME", "type": "String", "required": True, "desc": "产品名称"},
    "spec": {"e10": "ITEM_SPEC", "type": "String", "required": False, "desc": "规格"},
    "unit_no": {"e10": "UNIT_ID_UNIT_CODE", "type": "String", "required": True, "desc": "单位编号"},
    "item_type": {"e10": "ITEM_TYPE", "type": "String", "required": False, "desc": "品号属性"},
}


def get_field_doc(obj: str, category: str = "header") -> dict:
    """获取字段文档

    Args:
        obj: 业务对象 (purchase_receipt / sales_issue / material)
        category: 字段类别 (header / detail)
    """
    mapping = {
        ("purchase_receipt", "header"): PURCHASE_RECEIPT_HEADER_FIELDS,
        ("purchase_receipt", "detail"): PURCHASE_RECEIPT_DETAIL_FIELDS,
        ("sales_issue", "header"): SALES_ISSUE_HEADER_FIELDS,
        ("sales_issue", "detail"): SALES_ISSUE_DETAIL_FIELDS,
        ("material", "header"): MATERIAL_FIELDS,
    }
    return mapping.get((obj, category), {})
