"use client";

import { useEffect } from "react";
import { useStore } from "@/lib/store";

export function RatingsLoader() {
  const { setProfessorRatings, setGradeDistributions } = useStore();

  useEffect(() => {
    fetch("/professor_ratings.json")
      .then((res) => res.json())
      .then((data) => {
        // Strip (0.0, 0 ratings) sentinels so the UI shows "no rating" instead of 0/5.
        const cleaned: typeof data = {};
        for (const [name, r] of Object.entries<any>(data)) {
          if (r && r.num_ratings > 0 && r.quality > 0) cleaned[name] = r;
        }
        setProfessorRatings(cleaned);
      })
      .catch(() => {});

    fetch("/grade_distributions.json")
      .then((res) => res.json())
      .then((data) => {
        const clean: any = {};
        for (const [k, v] of Object.entries<any>(data)) {
          if (k !== "_metadata" && v && typeof v.avg_gpa === "number") clean[k] = v;
        }
        setGradeDistributions(clean);
      })
      .catch(() => {});
  }, [setProfessorRatings, setGradeDistributions]);

  return null;
}
