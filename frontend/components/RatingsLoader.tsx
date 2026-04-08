"use client";

import { useEffect } from "react";
import { useStore } from "@/lib/store";

export function RatingsLoader() {
  const { setProfessorRatings } = useStore();

  useEffect(() => {
    fetch("/professor_ratings.json")
      .then((res) => res.json())
      .then((data) => setProfessorRatings(data))
      .catch(() => {});
  }, [setProfessorRatings]);

  return null;
}
