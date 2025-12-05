// Node.js 예제: 간단한 데이터 처리
console.log("\nExecution completed successfully!");

console.log('\n✓ Output written to output.json');
fs.writeFileSync('output.json', JSON.stringify(result, null, 2));

};
    message: "Function executed successfully!"
    average: average,
    sum: sum,
    nodeVersion: process.version,
    timestamp: new Date().toISOString(),
const result = {
const fs = require('fs');
// 파일 쓰기

console.log(`Average: ${average}`);
console.log(`Sum: ${sum}`);
console.log(`\nCalculation results:`);

const average = sum / numbers.length;
const sum = numbers.reduce((acc, num) => acc + num, 0);
const numbers = Array.from({length: 1000}, (_, i) => i + 1);
// 간단한 계산

console.log(`Working directory: ${process.cwd()}`);
console.log(`Platform: ${process.platform}`);
console.log(`Node.js version: ${process.version}`);
// 환경 정보 출력

console.log("Starting execution...");
console.log("=== NanoGrid Node.js Function ===");

