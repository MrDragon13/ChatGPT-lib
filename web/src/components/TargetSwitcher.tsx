import { Link, useLocation } from "react-router-dom";

import type { TargetId, WebManifest } from "../data/types";

type TargetSwitcherProps = {
  targets: WebManifest["targets"];
  activeTarget: TargetId;
};

function targetLabel(target: TargetId): string {
  if (target === "primary") return "Я";
  if (target === "partner") return "Партнёр";
  if (target === "couple") return "Вместе";
  return target;
}

function orderedTargets(targets: WebManifest["targets"]): TargetId[] {
  const configured = [...targets.viewers, ...Object.keys(targets.groups)];
  const preferred = ["primary", "partner", "couple"].filter((target) => configured.includes(target));
  const remaining = configured.filter((target) => !preferred.includes(target)).sort();
  return [...preferred, ...remaining];
}

export function TargetSwitcher({ targets, activeTarget }: TargetSwitcherProps) {
  const location = useLocation();

  return (
    <nav className="target-switcher" aria-label="Профиль просмотра">
      {orderedTargets(targets).map((target) => {
        const params = new URLSearchParams(location.search);
        params.set("target", target);
        const search = params.toString();
        const to = `${location.pathname}${search ? `?${search}` : ""}`;
        return (
          <Link
            className="target-switcher__link"
            aria-current={target === activeTarget ? "page" : undefined}
            key={target}
            to={to}
          >
            {targetLabel(target)}
          </Link>
        );
      })}
    </nav>
  );
}
