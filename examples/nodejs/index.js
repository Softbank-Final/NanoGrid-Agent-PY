// Node.js 예제: 간단한 데이터 처리

console.log("=== NanoGrid Node.js Function ===");
console.log("Starting execution...");

// 환경 정보 출력
console.log(`Node.js version: ${process.version}`);
console.log(`Platform: ${process.platform}`);
console.log(`Working directory: ${process.cwd()}`);

// 간단한 계산
const numbers = Array.from({length: 1000}, (_, i) => i + 1);
const sum = numbers.reduce((acc, num) => acc + num, 0);
const average = sum / numbers.length;

console.log(`\nCalculation results:`);
console.log(`Sum: ${sum}`);
console.log(`Average: ${average}`);

// 파일 쓰기
const fs = require('fs');

const result = {
    timestamp: new Date().toISOString(),
    nodeVersion: process.version,
    sum: sum,
    average: average,
    message: "Function executed successfully!"
};

fs.writeFileSync('output.json', JSON.stringify(result, null, 2));
console.log('\n✓ Output written to output.json');

console.log("\nExecution completed successfully!");
