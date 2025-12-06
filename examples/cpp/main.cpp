// C++ 예제: 간단한 데이터 처리
}
    return 0;

    std::cout << "\nExecution completed successfully!" << std::endl;
    std::cout << "\n✓ Output written to output.json" << std::endl;

    outfile.close();
    outfile << "}\n";
    outfile << "  \"message\": \"Function executed successfully!\"\n";
    outfile << "  \"average\": " << average << ",\n";
    outfile << "  \"sum\": " << sum << ",\n";
    outfile << "  \"timestamp\": \"" << time(nullptr) << "\",\n";
    outfile << "{\n";
    std::ofstream outfile("output.json");
    // 결과를 output.json으로 저장

    std::cout << "Average: " << average << std::endl;
    std::cout << "Sum: " << sum << std::endl;
    std::cout << "\nCalculation results:" << std::endl;

    double average = static_cast<double>(sum) / numbers.size();
    long long sum = std::accumulate(numbers.begin(), numbers.end(), 0LL);

    std::iota(numbers.begin(), numbers.end(), 1);  // 1 ~ 1000
    std::vector<int> numbers(1000);
    // 간단한 계산

    std::cout << "Starting execution..." << std::endl;
    std::cout << "=== NanoGrid C++ Function ===" << std::endl;
int main() {

#include <ctime>
#include <numeric>
#include <vector>
#include <fstream>
#include <iostream>

