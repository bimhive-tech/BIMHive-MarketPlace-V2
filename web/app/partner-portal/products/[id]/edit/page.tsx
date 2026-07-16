"use client";

import { use, useEffect, useState } from "react";

import { ProductForm } from "@/features/admin/ProductForm/ProductForm";
import { me } from "@/lib/auth";

export default function EditPartnerProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [partnerName, setPartnerName] = useState("");

  useEffect(() => {
    me().then((user) => setPartnerName(user?.partner?.name ?? ""));
  }, []);

  return <ProductForm productId={Number(id)} mode="partner" partnerName={partnerName} />;
}
