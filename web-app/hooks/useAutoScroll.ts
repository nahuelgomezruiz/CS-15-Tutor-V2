import { useRef, useEffect } from "react";

export const useAutoScroll = (dependencies: any[]) => {
  const chatRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  const handleScroll = () => {
    if (!chatRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatRef.current;
    // Within 50px from the bottom counts as "at bottom"
    autoScrollRef.current = scrollHeight - scrollTop <= clientHeight + 50;
  };

  // Scroll to the bottom whenever dependencies change, but only if the user was already at the bottom
  useEffect(() => {
    if (chatRef.current && autoScrollRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, dependencies);

  return {
    chatRef,
    handleScroll
  };
}; 