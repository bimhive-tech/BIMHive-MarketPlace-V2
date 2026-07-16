"use client";

import { useEffect, useState } from "react";

import { ProductForm } from "@/features/admin/ProductForm/ProductForm";
import { me } from "@/lib/auth";

export default function NewPartnerProductPage() {
  const [partnerName, setPartnerName] = useState("");

  useEffect(() => {
    me().then((user) => setPartnerName(user?.partner?.name ?? ""));
  }, []);

  return <ProductForm mode="partner" partnerName={partnerName} />;
}
