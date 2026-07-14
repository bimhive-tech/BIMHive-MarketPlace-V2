"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { getAccountDownloads, type AccountDownload } from "@/lib/accountApi";

import styles from "./DownloadsList.module.css";

export function DownloadsList() {
  const [downloads, setDownloads] = useState<AccountDownload[] | null>(null);

  useEffect(() => {
    getAccountDownloads()
      .then(setDownloads)
      .catch(() => setDownloads([]));
  }, []);

  if (downloads === null) return <p className={styles.loading}>Loading your downloads…</p>;

  if (downloads.length === 0) {
    return (
      <EmptyState
        icon="download"
        title="Nothing to download yet"
        text="Files for products you own will appear here, served over secure, expiring links."
        actionLabel="Browse the marketplace"
        actionHref="/catalog"
      />
    );
  }

  return (
    <div className={styles.list}>
      {downloads.map((item) => (
        <div key={item.id} className={styles.card}>
          <div className={styles.head}>
            {item.cover_image_url && (
              <Image src={item.cover_image_url} alt="" width={56} height={56} className={styles.thumb} />
            )}
            <span className={styles.product}>{item.product_name}</span>
          </div>

          {item.files.length === 0 ? (
            <p className={styles.noFiles}>No build has been uploaded for this product yet.</p>
          ) : (
            <div className={styles.files}>
              {item.files.map((file) => (
                <div key={file.id} className={styles.file}>
                  <span className={styles.fileMeta}>
                    {file.revit_version ? `Revit ${file.revit_version}` : "All versions"} · v
                    {file.version_label}
                    {file.is_current && <span className={styles.current}>current</span>}
                  </span>
                  <Button href={file.download_url} external variant="secondary" size="md">
                    <Icon name="download" size={14} /> Download
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
