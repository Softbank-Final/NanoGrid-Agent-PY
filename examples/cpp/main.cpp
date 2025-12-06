// C++ 예제: 간단한 데이터 처리
#include <iostream>
#include <fstream>
#include <vector>
#include <numeric>
#include <ctime>

int main() {
    std::cout << "=== NanoGrid C++ Function ===" << std::endl;
    std::cout << "Starting execution..." << std::endl;

    // 간단한 계산
    std::vector<int> numbers(1000);
    std::iota(numbers.begin(), numbers.end(), 1);  // 1 ~ 1000

    long long sum = std::accumulate(numbers.begin(), numbers.end(), 0LL);
    double average = static_cast<double>(sum) / numbers.size();

    std::cout << "\nCalculation results:" << std::endl;
    std::cout << "Sum: " << sum << std::endl;
    std::cout << "Average: " << average << std::endl;

    // 결과를 output.json으로 저장
    std::ofstream outfile("output.json");
    outfile << "{\n";
    outfile << "  \"timestamp\": \"" << time(nullptr) << "\",\n";
    outfile << "  \"sum\": " << sum << ",\n";
    outfile << "  \"average\": " << average << ",\n";
    outfile << "  \"message\": \"Function executed successfully!\"\n";
    outfile << "}\n";
    outfile.close();

    std::cout << "\n✓ Output written to output.json" << std::endl;
    std::cout << "\nExecution completed successfully!" << std::endl;

    return 0;
}
