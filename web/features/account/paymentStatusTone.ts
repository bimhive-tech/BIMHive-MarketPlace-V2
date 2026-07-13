type Tone = "neutral" | "success" | "warning" | "error" | "gold";

/** Shared by OrdersList and LicensesList — both render ProductPurchase.payment_status. */
export function paymentStatusTone(status: string): Tone {
  switch (status) {
    case "paid":
      return "success";
    case "pending":
      return "warning";
    case "failed":
    case "revoked":
      return "error";
    default:
      return "neutral"; // refunded, cancelled
  }
}
