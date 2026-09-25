import React from 'react';

export default function TopQuestions({ questions }) {
  // questions expected: [{ text: "What are your business hours?", count: 42 }, ...]
  return (
    <div className="bg-white p-4 rounded shadow h-full">
      <h2 className="text-lg font-semibold mb-4">Top User Questions</h2>
      {questions && questions.length > 0 ? (
        <ul className="space-y-3">
          {questions.map((q, idx) => (
            <li key={idx} className="flex justify-between items-center bg-gray-50 p-3 rounded">
              <span className="text-gray-700 text-sm truncate pr-4">{q.text}</span>
              <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full whitespace-nowrap">
                {q.count} times
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-gray-500 text-sm">No queries recorded yet.</p>
      )}
    </div>
  );
}
