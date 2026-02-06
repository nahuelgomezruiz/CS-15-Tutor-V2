import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export const Button: React.FC<ButtonProps> = ({ children, ...props }) => {
  return (
    <button {...props} className={`px-4 py-2 rounded-full bg-cyan-600 text-black ${props.className}`}>
      {children}
    </button>
  );
};