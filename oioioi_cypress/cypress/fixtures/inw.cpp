/* Zadanie: Inwazja kosmitów
   Autor: Tomasz Idziaszek
   AMPPZ 2012

   Rozwiązanie wzorcowe O(n)
*/

#include <cstdio>
#include <algorithm>
using namespace std;

const int N=1000000;
int n,a[N];
long long d[N+1];

int main() {
   scanf("%d",&n);
   for(int i=0; i<n; ++i)
      scanf("%d",&a[i]);
   d[0] = 0;
   d[1] = a[0];
   for(int i=1; i<n; ++i)
      d[i+1] = max(d[i], d[i-1] + a[i]);
   printf("%lld\n", d[n]);
}
