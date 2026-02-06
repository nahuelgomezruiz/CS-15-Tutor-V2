import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}


export const Input: React.FC<InputProps> = (props) => {
  return (
    <input
      {...props}
      className={`border p-2 rounded focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 ${props.className}`}
    />
  );
};
