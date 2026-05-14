from posawesome.posawesome.doctype.pos_coupon.pos_coupon import update_coupon_code_count


def update_coupon(doc, transaction_type):
    for coupon in doc.posa_coupons:
        if coupon.applied:
            update_coupon_code_count(coupon.coupon, transaction_type)
