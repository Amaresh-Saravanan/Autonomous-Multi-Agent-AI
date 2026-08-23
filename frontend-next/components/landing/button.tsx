import type { ComponentProps, ReactNode } from "react";

type ButtonProps = Omit<ComponentProps<"button">, "onClick"> & {
  href?: string;
  size?: "sm" | "lg";
  variant?: "outline";
  children?: ReactNode;
  onClick?: () => void;
};

export function Button({ className = "", href, size, variant, onClick, ...props }: ButtonProps) {
  const classes = `inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 ${className}`;

  if (href) {
    return (
      <a href={href} className={classes} onClick={onClick}>
        {props.children}
      </a>
    );
  }

  return <button className={classes} onClick={onClick} {...props} />;
}
