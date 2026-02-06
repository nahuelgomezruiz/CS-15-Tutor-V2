import React, { useEffect, useState } from 'react';

interface HealthBarProps {
  currentPoints: number;
  maxPoints: number;
  timeUntilNextRegen: number;
}

export const HealthBar: React.FC<HealthBarProps> = ({ 
  currentPoints, 
  maxPoints, 
  timeUntilNextRegen 
}) => {
  const [timeLeft, setTimeLeft] = useState(timeUntilNextRegen);
  
  useEffect(() => {
    setTimeLeft(timeUntilNextRegen);
  }, [timeUntilNextRegen]);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1));
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);
  
  const percentage = (currentPoints / maxPoints) * 100;
  
  // Determine color based on percentage
  const getBarColor = () => {
    if (percentage > 60) return 'bg-emerald-500';
    if (percentage > 30) return 'bg-amber-500';
    return 'bg-red-500';
  };
  
  return (
    <div className="w-full mb-3 flex items-center justify-between gap-4">
      <h1 className="text-xl font-sans font-medium text-white">CS 15 Tutor</h1>
      
      <div className="flex-1 max-w-48">
        <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${getBarColor()}`}
            style={{ width: `${percentage}%` }}
          >
            <div className="h-full bg-gradient-to-r from-transparent to-white/20" />
          </div>
        </div>
        
        {currentPoints === 0 && (
          <p className="mt-1 text-xs text-red-400 text-right opacity-80">
            Out of queries. Please wait.
          </p>
        )}
      </div>
    </div>
  );
}; 